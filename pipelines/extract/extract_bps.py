from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from pipelines.utils.api_client import get_json
from pipelines.utils.bps_config import BPSConfiguration

BASE_URL = "https://webapi.bps.go.id/v1/api"
SOURCE_CODE = "bps"
SOURCE_NAME = "Badan Pusat Statistik"
MAX_PAGES = 1000


@dataclass(frozen=True)
class BPSRequest:
    resource: str
    source_url: str
    parameters: dict[str, str | int]
    payload: dict[str, Any]


@dataclass(frozen=True)
class BPSExtraction:
    province_request: BPSRequest
    period_requests: dict[int, tuple[BPSRequest, ...]]
    data_requests: dict[int, BPSRequest]

    @property
    def requests(self) -> tuple[BPSRequest, ...]:
        ordered: list[BPSRequest] = [self.province_request]
        for variable_id in sorted(self.period_requests):
            ordered.extend(self.period_requests[variable_id])
            ordered.append(self.data_requests[variable_id])
        return tuple(ordered)


def _validate_payload(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"Respons BPS untuk {context} bukan object JSON")
    if payload.get("status") != "OK":
        status = str(payload.get("status", "tidak tersedia"))
        raise ValueError(f"Respons BPS untuk {context} berstatus {status}")
    availability = payload.get("data-availability")
    if availability is not None and availability != "available":
        raise ValueError(f"Data BPS untuk {context} tidak tersedia")
    return payload


def parse_paginated_response(
    payload: dict[str, Any], context: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = payload.get("data")
    if (
        not isinstance(data, list)
        or len(data) != 2
        or not isinstance(data[0], dict)
        or not isinstance(data[1], list)
        or any(not isinstance(item, dict) for item in data[1])
    ):
        raise ValueError(f"Respons paginated BPS untuk {context} tidak valid")
    metadata = data[0]
    try:
        page = int(metadata["page"])
        pages = int(metadata["pages"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"Metadata pagination BPS untuk {context} tidak valid"
        ) from error
    if page < 1 or pages < 1 or page > pages or pages > MAX_PAGES:
        raise ValueError(f"Rentang pagination BPS untuk {context} tidak valid")
    return metadata, data[1]


class BPSClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        api_key = api_key.strip()
        if not api_key:
            raise RuntimeError("BPS_API_KEY belum dikonfigurasi")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_environment(cls, base_url: str = BASE_URL) -> BPSClient:
        return cls(os.environ.get("BPS_API_KEY", ""), base_url)

    def request(
        self,
        resource: str,
        parameters: dict[str, str | int],
        *,
        context: str,
    ) -> BPSRequest:
        resource = resource.strip("/")
        if not resource:
            raise ValueError("Resource BPS tidak boleh kosong")
        path = "/".join(
            [resource]
            + [
                component
                for key, value in parameters.items()
                for component in (
                    quote(str(key), safe=""),
                    quote(str(value), safe=";:"),
                )
            ]
        )
        source_url = f"{self.base_url}/{path}"
        authenticated_url = f"{source_url}/key/{quote(self._api_key, safe='')}/"
        try:
            payload = get_json(authenticated_url)
        except (requests.RequestException, ValueError):
            raise RuntimeError(f"Permintaan BPS gagal untuk {context}") from None
        validated = _validate_payload(payload, context)
        return BPSRequest(
            resource=resource,
            source_url=source_url,
            parameters=dict(parameters),
            payload=validated,
        )

    def list_paginated(
        self,
        model: str,
        *,
        domain: str,
        language: str = "ind",
        filters: dict[str, str | int] | None = None,
    ) -> tuple[tuple[BPSRequest, ...], list[dict[str, Any]]]:
        base_parameters: dict[str, str | int] = {
            "model": model,
            "lang": language,
            "domain": domain,
        }
        if filters:
            base_parameters.update(filters)
        context = f"model={model}, domain={domain}"
        first = self.request("list", {**base_parameters, "page": 1}, context=context)
        metadata, rows = parse_paginated_response(first.payload, context)
        pages = int(metadata["pages"])
        requests_made = [first]
        all_rows = list(rows)
        for page in range(2, pages + 1):
            request = self.request(
                "list", {**base_parameters, "page": page}, context=context
            )
            page_metadata, page_rows = parse_paginated_response(
                request.payload, context
            )
            if int(page_metadata["page"]) != page:
                raise ValueError(
                    f"BPS mengembalikan halaman {page_metadata['page']} saat "
                    f"halaman {page} diminta untuk {context}"
                )
            requests_made.append(request)
            all_rows.extend(page_rows)
        return tuple(requests_made), all_rows


def extract_bps(configuration: BPSConfiguration, client: BPSClient) -> BPSExtraction:
    source = configuration.source
    province_request = client.request(
        "domain", {"type": "prov"}, context="daftar domain provinsi"
    )
    # Daftar periode diambil lebih dahulu agar metadata dan pagination
    # tervalidasi sebelum tabel dinamis diminta.
    period_requests: dict[int, tuple[BPSRequest, ...]] = {}
    data_requests: dict[int, BPSRequest] = {}
    for variable_id in configuration.indicators:
        requests_made, _ = client.list_paginated(
            "th",
            domain=source.domain,
            language=source.language,
            filters={"var": variable_id},
        )
        period_requests[variable_id] = requests_made
        data_requests[variable_id] = client.request(
            "list",
            {
                "model": "data",
                "lang": source.language,
                "domain": source.domain,
                "var": variable_id,
            },
            context=f"data variabel {variable_id}",
        )
    return BPSExtraction(
        province_request=province_request,
        period_requests=period_requests,
        data_requests=data_requests,
    )
