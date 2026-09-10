from datetime import date

import pytest

from pipelines.extract.extract_bank_indonesia import (
    XLSX_CONTENT_TYPE,
    download_bi_rate,
    download_jisdor,
)
from pipelines.utils.bank_indonesia_config import (
    load_bank_indonesia_configuration,
)
from tests.pipeline.bank_indonesia_fixtures import bi_rate_workbook, jisdor_xml


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.content = payload
        self.text = payload.decode(errors="replace")
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, landing_html: bytes) -> None:
        self.landing_html = landing_html
        self.posted_data: dict[str, str] | None = None
        self.jisdor_parameters: dict[str, str] | None = None

    def get(self, url, *, params=None, headers=None, timeout=None):
        if params is None:
            return FakeResponse(self.landing_html, "text/html; charset=utf-8")
        self.jisdor_parameters = params
        return FakeResponse(jisdor_xml(), "text/xml; charset=utf-8")

    def post(self, url, *, data=None, headers=None, timeout=None):
        self.posted_data = data
        response = FakeResponse(bi_rate_workbook(), XLSX_CONTENT_TYPE)
        response.headers["Content-Disposition"] = "attachment; filename=data.xlsx"
        return response


def landing_page(*, include_export: bool = True) -> bytes:
    export = (
        '<input type="submit" name="ctl$ButtonExport" id="ctl_ButtonExport" '
        'value="Unduh" />'
        if include_export
        else ""
    )
    return (
        '<html><form><input type="hidden" name="__VIEWSTATE" value="state" />'
        '<input type="hidden" name="__EVENTVALIDATION" value="validation" />'
        f"{export}</form></html>"
    ).encode()


def test_bi_rate_downloader_submits_official_export_form():
    configuration = load_bank_indonesia_configuration()
    session = FakeSession(landing_page())

    resource = download_bi_rate(configuration, session)

    assert resource.payload == bi_rate_workbook()
    assert resource.content_type == XLSX_CONTENT_TYPE
    assert session.posted_data == {
        "__VIEWSTATE": "state",
        "__EVENTVALIDATION": "validation",
        "ctl$ButtonExport": "Unduh",
    }


def test_bi_rate_downloader_rejects_changed_form():
    configuration = load_bank_indonesia_configuration()
    session = FakeSession(landing_page(include_export=False))

    with pytest.raises(RuntimeError, match="Form unduhan BI-Rate berubah"):
        download_bi_rate(configuration, session)


def test_jisdor_downloader_uses_iso_date_range():
    configuration = load_bank_indonesia_configuration()
    session = FakeSession(landing_page())

    resource = download_jisdor(
        configuration,
        date(2026, 1, 1),
        date(2026, 2, 28),
        session,
    )

    assert resource.payload == jisdor_xml()
    assert session.jisdor_parameters == {
        "mts": "USD",
        "startDate": "2026-01-01",
        "endDate": "2026-02-28",
    }
