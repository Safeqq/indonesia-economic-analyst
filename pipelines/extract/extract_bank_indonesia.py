from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Any

import requests

from pipelines.utils.api_client import create_retry_session
from pipelines.utils.bank_indonesia_config import BankIndonesiaConfiguration

SOURCE_CODE = "bank_indonesia"
BI_TIMEOUT = (15, 120)
BI_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
)
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XML_CONTENT_TYPES = {"application/xml", "text/xml"}


@dataclass(frozen=True)
class BankIndonesiaResource:
    name: str
    source_url: str
    request_method: str
    parameters: dict[str, str]
    content_type: str
    content_disposition: str | None
    payload: bytes


@dataclass(frozen=True)
class BankIndonesiaExtraction:
    bi_rate: BankIndonesiaResource
    jisdor: BankIndonesiaResource

    @property
    def resources(self) -> tuple[BankIndonesiaResource, ...]:
        return (self.bi_rate, self.jisdor)


class _ExportFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_fields: dict[str, str] = {}
        self.export_field: tuple[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "input":
            return
        attributes = {key.casefold(): value or "" for key, value in attrs}
        name = attributes.get("name", "")
        input_type = attributes.get("type", "text").casefold()
        value = attributes.get("value", "")
        element_id = attributes.get("id", "")
        if name and input_type == "hidden":
            self.hidden_fields[name] = value
        if (
            name
            and input_type == "submit"
            and (
                element_id.endswith("ButtonExport")
                or value.strip().casefold() in {"unduh", "download"}
            )
        ):
            self.export_field = (name, value)


def _content_type(response: Any) -> str:
    return response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()


def _prepare_session() -> requests.Session:
    session = create_retry_session()
    session.headers.update(
        {
            "User-Agent": BI_USER_AGENT,
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        }
    )
    return session


def download_bi_rate(
    configuration: BankIndonesiaConfiguration,
    session: requests.Session,
) -> BankIndonesiaResource:
    page_url = configuration.bi_rate.page_url
    try:
        landing = session.get(
            page_url,
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=BI_TIMEOUT,
        )
        landing.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Unduhan halaman BI-Rate gagal: {error}") from error

    if _content_type(landing) != "text/html":
        raise RuntimeError(
            "Format halaman BI-Rate berubah: "
            f"Content-Type={landing.headers.get('Content-Type', 'kosong')!r}"
        )
    parser = _ExportFormParser()
    parser.feed(landing.text)
    required_hidden = {"__VIEWSTATE", "__EVENTVALIDATION"}
    missing_hidden = sorted(required_hidden.difference(parser.hidden_fields))
    if missing_hidden or parser.export_field is None:
        raise RuntimeError(
            "Form unduhan BI-Rate berubah: "
            f"hidden_missing={missing_hidden}, export_button="
            f"{parser.export_field is not None}"
        )

    form_data = dict(parser.hidden_fields)
    export_name, export_value = parser.export_field
    form_data[export_name] = export_value
    try:
        response = session.post(
            page_url,
            data=form_data,
            headers={
                "Accept": f"{XLSX_CONTENT_TYPE},application/octet-stream;q=0.9",
                "Referer": page_url,
            },
            timeout=BI_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Unduhan workbook BI-Rate gagal: {error}") from error

    actual_content_type = _content_type(response)
    if actual_content_type != XLSX_CONTENT_TYPE or not response.content.startswith(
        b"PK"
    ):
        raise RuntimeError(
            "Format unduhan BI-Rate berubah: diharapkan XLSX, "
            f"Content-Type={response.headers.get('Content-Type', 'kosong')!r}"
        )
    return BankIndonesiaResource(
        name="bi_rate",
        source_url=page_url,
        request_method="POST",
        parameters={"export": export_value},
        content_type=actual_content_type,
        content_disposition=response.headers.get("Content-Disposition"),
        payload=response.content,
    )


def download_jisdor(
    configuration: BankIndonesiaConfiguration,
    start_date: date,
    end_date: date,
    session: requests.Session,
) -> BankIndonesiaResource:
    if start_date > end_date:
        raise ValueError("Tanggal awal JISDOR tidak boleh melewati tanggal akhir")
    definition = configuration.jisdor
    parameters = {
        "mts": definition.currency,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }
    try:
        response = session.get(
            definition.endpoint_url,
            params=parameters,
            headers={"Accept": "application/xml,text/xml;q=0.9"},
            timeout=BI_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Unduhan JISDOR gagal: {error}") from error

    actual_content_type = _content_type(response)
    if (
        actual_content_type not in XML_CONTENT_TYPES
        or not response.content.lstrip().startswith(b"<?xml")
    ):
        raise RuntimeError(
            "Format unduhan JISDOR berubah: diharapkan XML, "
            f"Content-Type={response.headers.get('Content-Type', 'kosong')!r}"
        )
    return BankIndonesiaResource(
        name="jisdor",
        source_url=definition.endpoint_url,
        request_method="GET",
        parameters=parameters,
        content_type=actual_content_type,
        content_disposition=response.headers.get("Content-Disposition"),
        payload=response.content,
    )


def extract_bank_indonesia(
    configuration: BankIndonesiaConfiguration,
    start_date: date,
    end_date: date,
    *,
    session: requests.Session | None = None,
) -> BankIndonesiaExtraction:
    owned_session = session is None
    active_session = session or _prepare_session()
    try:
        bi_rate = download_bi_rate(configuration, active_session)
        jisdor = download_jisdor(configuration, start_date, end_date, active_session)
    finally:
        if owned_session:
            active_session.close()
    return BankIndonesiaExtraction(bi_rate=bi_rate, jisdor=jisdor)
