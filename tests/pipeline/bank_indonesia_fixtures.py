from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from pipelines.extract.extract_bank_indonesia import (
    XLSX_CONTENT_TYPE,
    BankIndonesiaExtraction,
    BankIndonesiaResource,
)


def bi_rate_workbook(
    *,
    value_header: str = "BI-7Day-RR",
    sheet_name: str = "BI-7Day-RR",
) -> bytes:
    strings = [
        sheet_name,
        "NO",
        "Tanggal",
        value_header,
        "17 Desember 2025",
        "5.75 %",
        "19 Februari 2026",
        "5.50 %",
    ]
    shared_strings = "".join(f"<si><t>{escape(item)}</t></si>" for item in strings)
    workbook = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" '
        'r:id="rId1" /></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml" /></Relationships>'
    )
    worksheet = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData>'
        '<row r="3"><c r="A3" t="s"><v>0</v></c></row>'
        '<row r="5">'
        '<c r="A5" t="s"><v>1</v></c>'
        '<c r="B5" t="s"><v>2</v></c>'
        '<c r="C5" t="s"><v>3</v></c>'
        "</row>"
        '<row r="6">'
        '<c r="A6"><v>1</v></c>'
        '<c r="B6" t="s"><v>4</v></c>'
        '<c r="C6" t="s"><v>5</v></c>'
        "</row>"
        '<row r="7">'
        '<c r="A7"><v>2</v></c>'
        '<c r="B7" t="s"><v>6</v></c>'
        '<c r="C7" t="s"><v>7</v></c>'
        "</row>"
        "</sheetData></worksheet>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/'
            f'spreadsheetml/2006/main">{shared_strings}</sst>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buffer.getvalue()


def jisdor_xml(*, extra_field: bool = False) -> bytes:
    rows = (
        ("1", "2026-01-02T00:00:00+07:00", "16000.00"),
        ("2", "2026-01-30T00:00:00+07:00", "16200.00"),
        ("3", "2026-02-02T00:00:00+07:00", "16300.00"),
        ("4", "2026-02-27T00:00:00+07:00", "16500.00"),
    )
    xml_rows = []
    for identifier, observation_date, value in rows:
        extra = "<unexpected>drift</unexpected>" if extra_field else ""
        xml_rows.append(
            "<Table>"
            f"<id_subkursasing>{identifier}</id_subkursasing>"
            "<lnk_subkursasing>23</lnk_subkursasing>"
            "<nil_subkursasing>1.00</nil_subkursasing>"
            f"<beli_subkursasing>{value}</beli_subkursasing>"
            f"<jual_subkursasing>{value}</jual_subkursasing>"
            f"<tgl_subkursasing>{observation_date}</tgl_subkursasing>"
            "<mts_subkursasing>USD  </mts_subkursasing>"
            f"{extra}</Table>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<DataSet xmlns="http://tempuri.org/"><diffgram>'
        f'<NewDataSet xmlns="">{"".join(xml_rows)}</NewDataSet>'
        "</diffgram></DataSet>"
    ).encode()


def extraction_fixture() -> BankIndonesiaExtraction:
    return BankIndonesiaExtraction(
        bi_rate=BankIndonesiaResource(
            name="bi_rate",
            source_url="https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx",
            request_method="POST",
            parameters={"export": "Unduh"},
            content_type=XLSX_CONTENT_TYPE,
            content_disposition="attachment; filename=BI-7Day-RR.xlsx",
            payload=bi_rate_workbook(),
        ),
        jisdor=BankIndonesiaResource(
            name="jisdor",
            source_url=(
                "https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursJisdor3"
            ),
            request_method="GET",
            parameters={
                "mts": "USD",
                "startDate": "2026-01-01",
                "endDate": "2026-02-28",
            },
            content_type="text/xml",
            content_disposition=None,
            payload=jisdor_xml(),
        ),
    )
