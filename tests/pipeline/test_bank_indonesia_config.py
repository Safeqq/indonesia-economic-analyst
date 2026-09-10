from datetime import date

from pipelines.utils.bank_indonesia_config import (
    load_bank_indonesia_configuration,
)


def test_bank_indonesia_configuration_is_explicit():
    configuration = load_bank_indonesia_configuration()

    assert configuration.source.code == "bank_indonesia"
    assert configuration.source.default_start_date == date(2016, 8, 1)
    assert configuration.bi_rate.source_format == "xlsx"
    assert "BI-7Day-RR" in configuration.bi_rate.sheet_names
    assert configuration.bi_rate.date_columns == ("Tanggal", "Periode")
    assert configuration.jisdor.source_format == "xml"
    assert configuration.jisdor.fields["date"] == "tgl_subkursasing"
    assert configuration.jisdor.currency == "USD"
