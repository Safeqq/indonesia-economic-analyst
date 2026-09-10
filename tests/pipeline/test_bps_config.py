from pipelines.utils.bps_config import (
    load_bps_configuration,
    load_bps_provinces,
)


def test_production_bps_catalog_has_two_official_variables():
    configuration = load_bps_configuration()

    assert set(configuration.indicators) == {543, 1975}
    assert configuration.source.domain == "0000"


def test_production_province_mapping_has_38_unique_official_codes():
    configuration = load_bps_provinces()

    assert len(configuration.provinces) == 38
    assert len(set(configuration.provinces)) == 38
    assert all(len(code) == 4 and code.isdigit() for code in configuration.provinces)
    assert configuration.parent_region_code == "IDN"
