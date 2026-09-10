from __future__ import annotations

from pipelines.extract.extract_bps import BPSExtraction, BPSRequest
from pipelines.utils.bps_config import (
    BPSConfiguration,
    BPSIndicatorDefinition,
    BPSProvinceConfiguration,
    BPSSourceDefinition,
)


def configuration() -> BPSConfiguration:
    return BPSConfiguration(
        source=BPSSourceDefinition(
            code="bps",
            name="Badan Pusat Statistik",
            base_url="https://webapi.bps.go.id/v1/api",
            domain="0000",
            language="ind",
        ),
        indicators={
            1975: BPSIndicatorDefinition(
                variable_id=1975,
                code_prefix="BPS.1975",
                name="Jumlah Penduduk Pertengahan Tahun",
                frequency="annual",
            ),
            543: BPSIndicatorDefinition(
                variable_id=543,
                code_prefix="BPS.543",
                name="Tingkat Pengangguran Terbuka Menurut Provinsi",
                frequency="annual",
            ),
        },
    )


def province_configuration() -> BPSProvinceConfiguration:
    return BPSProvinceConfiguration(
        parent_region_code="IDN",
        provinces={"1100": "Aceh", "1200": "Sumatera Utara"},
    )


def _request(
    resource: str, source_url: str, parameters: dict, payload: dict
) -> BPSRequest:
    return BPSRequest(
        resource=resource,
        source_url=source_url,
        parameters=parameters,
        payload=payload,
    )


def data_payload(
    variable_id: int,
    *,
    unit: str = "Persen",
    include_second_province: bool = True,
    extra_content: dict[str, object] | None = None,
) -> dict:
    labels = {
        1975: "Jumlah Penduduk Pertengahan Tahun",
        543: "Tingkat Pengangguran Terbuka Menurut Provinsi",
    }
    content: dict[str, object] = {
        f"1100{variable_id}01010": 5.25,
        f"9999{variable_id}01010": 50.25,
    }
    if include_second_province:
        content[f"1200{variable_id}01010"] = 4.75
    if extra_content:
        content.update(extra_content)
    return {
        "status": "OK",
        "data-availability": "available",
        "var": [
            {
                "val": variable_id,
                "label": labels[variable_id],
                "unit": unit,
                "def": "Definisi resmi fixture",
                "note": "Catatan resmi fixture",
            }
        ],
        "turvar": [{"val": 0, "label": ""}],
        "labelvervar": "Provinsi",
        "vervar": [
            {"val": 1100, "label": "Aceh"},
            {"val": 1200, "label": "Sumatera Utara"},
            {"val": 9999, "label": "Indonesia"},
        ],
        "tahun": [{"val": 101, "label": "2023"}],
        "turtahun": [{"val": 0, "label": "Tahun"}],
        "datacontent": content,
    }


def extraction(
    *,
    second_variable_unit: str = "Persen",
    second_variable_complete: bool = True,
    second_variable_extra_content: dict[str, object] | None = None,
) -> BPSExtraction:
    domain_payload = {
        "status": "OK",
        "data-availability": "available",
        "data": [
            {"page": 1, "pages": 1, "per_page": 100, "count": 2, "total": 2},
            [
                {"domain_id": "1100", "domain_name": "Aceh"},
                {"domain_id": "1200", "domain_name": "Sumatera Utara"},
            ],
        ],
    }
    period_payload = {
        "status": "OK",
        "data-availability": "available",
        "data": [
            {"page": 1, "pages": 1, "per_page": 10, "count": 1, "total": 1},
            [{"th_id": 101, "th": 2023}],
        ],
    }
    province_request = _request(
        "domain",
        "https://webapi.bps.go.id/v1/api/domain/type/prov",
        {"type": "prov"},
        domain_payload,
    )
    period_requests = {
        variable_id: (
            _request(
                "list",
                (
                    "https://webapi.bps.go.id/v1/api/list/model/th/lang/ind/"
                    f"domain/0000/var/{variable_id}/page/1"
                ),
                {
                    "model": "th",
                    "lang": "ind",
                    "domain": "0000",
                    "var": variable_id,
                    "page": 1,
                },
                period_payload,
            ),
        )
        for variable_id in (1975, 543)
    }
    data_requests = {
        1975: _request(
            "list",
            "https://webapi.bps.go.id/v1/api/list/model/data/domain/0000/var/1975",
            {"model": "data", "domain": "0000", "var": 1975},
            data_payload(1975, unit="Ribu Jiwa"),
        ),
        543: _request(
            "list",
            "https://webapi.bps.go.id/v1/api/list/model/data/domain/0000/var/543",
            {"model": "data", "domain": "0000", "var": 543},
            data_payload(
                543,
                unit=second_variable_unit,
                include_second_province=second_variable_complete,
                extra_content=second_variable_extra_content,
            ),
        ),
    }
    return BPSExtraction(
        province_request=province_request,
        period_requests=period_requests,
        data_requests=data_requests,
    )
