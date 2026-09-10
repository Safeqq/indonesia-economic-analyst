from datetime import UTC, date, datetime

import pytest

from pipelines.transform.clean_bank_indonesia_data import (
    BankIndonesiaSchemaDriftError,
    clean_bank_indonesia,
    parse_bi_rate_xlsx,
    parse_jisdor_xml,
    validate_bank_indonesia_coverage,
    validate_bank_indonesia_value_ranges,
    validate_complete_month_range,
)
from pipelines.transform.validate_data import validate
from pipelines.utils.bank_indonesia_config import (
    load_bank_indonesia_configuration,
)
from tests.pipeline.bank_indonesia_fixtures import (
    bi_rate_workbook,
    extraction_fixture,
    jisdor_xml,
)


def test_bank_indonesia_parsers_read_official_shapes():
    configuration = load_bank_indonesia_configuration()

    rates = parse_bi_rate_xlsx(bi_rate_workbook(), configuration.bi_rate)
    jisdor = parse_jisdor_xml(jisdor_xml(), configuration.jisdor)

    assert [(item.effective_date, float(item.value)) for item in rates] == [
        (date(2025, 12, 17), 5.75),
        (date(2026, 2, 19), 5.5),
    ]
    assert len(jisdor) == 4
    assert jisdor[0].observation_date == date(2026, 1, 2)
    assert float(jisdor[-1].value) == 16500


def test_bi_rate_parser_reports_column_schema_drift():
    configuration = load_bank_indonesia_configuration()

    with pytest.raises(BankIndonesiaSchemaDriftError, match="Schema drift BI-Rate"):
        parse_bi_rate_xlsx(
            bi_rate_workbook(value_header="Suku Bunga Baru"),
            configuration.bi_rate,
        )


def test_jisdor_parser_reports_field_schema_drift():
    configuration = load_bank_indonesia_configuration()

    with pytest.raises(BankIndonesiaSchemaDriftError, match="Schema drift JISDOR"):
        parse_jisdor_xml(jisdor_xml(extra_field=True), configuration.jisdor)


def test_bank_indonesia_transform_aligns_two_monthly_series():
    configuration = load_bank_indonesia_configuration()
    cleaned = clean_bank_indonesia(
        extraction_fixture(),
        configuration,
        datetime(2026, 3, 1, tzinfo=UTC),
        date(2026, 1, 1),
        date(2026, 2, 28),
    )

    validate(cleaned.frame)
    validate_bank_indonesia_coverage(cleaned.frame, configuration)
    validate_bank_indonesia_value_ranges(cleaned.frame, configuration)

    assert cleaned.bi_rate_event_count == 2
    assert cleaned.jisdor_daily_count == 4
    assert cleaned.month_count == 2
    assert len(cleaned.frame) == 4
    rates = cleaned.frame.loc[
        cleaned.frame["indicator_code"].eq(configuration.bi_rate.code), "value"
    ].tolist()
    jisdor = cleaned.frame.loc[
        cleaned.frame["indicator_code"].eq(configuration.jisdor.code), "value"
    ].tolist()
    assert rates == [5.75, 5.5]
    assert jisdor == [16100.0, 16400.0]


def test_bank_indonesia_range_requires_complete_months():
    with pytest.raises(ValueError, match="akhir bulan kalender yang lengkap"):
        validate_complete_month_range(date(2026, 1, 1), date(2026, 2, 15))
