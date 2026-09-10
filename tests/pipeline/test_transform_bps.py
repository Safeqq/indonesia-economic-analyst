from datetime import UTC, datetime

import pytest

from pipelines.transform.clean_bps_data import (
    clean_bps,
    validate_bps_coverage,
    validate_bps_metadata,
    validate_bps_value_ranges,
)
from pipelines.transform.validate_data import validate
from tests.pipeline.bps_fixtures import (
    configuration,
    extraction,
    province_configuration,
)


def test_bps_transform_normalizes_official_provinces_and_metadata():
    cleaned = clean_bps(
        extraction(),
        configuration(),
        province_configuration(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    validate(cleaned.frame)
    validate_bps_metadata(cleaned.metadata, cleaned.frame)
    validate_bps_value_ranges(cleaned.frame)
    coverage = validate_bps_coverage(cleaned.frame, configuration(), cleaned.provinces)

    assert len(cleaned.frame) == 4
    assert set(cleaned.frame["region_code"]) == {"1100", "1200"}
    assert set(cleaned.frame["parent_region_code"]) == {"IDN"}
    assert set(cleaned.frame["indicator_code"]) == {
        "BPS.1975.TV0.TP0",
        "BPS.543.TV0.TP0",
    }
    assert set(coverage) == {1975, 543}
    assert len(cleaned.metadata) == 2


def test_incomplete_province_coverage_is_rejected():
    cleaned = clean_bps(
        extraction(second_variable_complete=False),
        configuration(),
        province_configuration(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="tidak memiliki satu periode lengkap"):
        validate_bps_coverage(cleaned.frame, configuration(), cleaned.provinces)


def test_unknown_datacontent_shape_is_rejected():
    with pytest.raises(ValueError, match="Schema datacontent"):
        clean_bps(
            extraction(second_variable_extra_content={"unexpected": 1}),
            configuration(),
            province_configuration(),
            datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_unit_change_creates_a_new_metadata_hash():
    first = clean_bps(
        extraction(second_variable_unit="Persen"),
        configuration(),
        province_configuration(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = clean_bps(
        extraction(second_variable_unit="Poin"),
        configuration(),
        province_configuration(),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    first_hash = first.metadata.set_index("indicator_code").loc[
        "BPS.543.TV0.TP0", "metadata_hash"
    ]
    second_hash = second.metadata.set_index("indicator_code").loc[
        "BPS.543.TV0.TP0", "metadata_hash"
    ]

    assert first_hash != second_hash


def test_invalid_tpt_range_is_rejected():
    source = extraction()
    source.data_requests[543].payload["datacontent"]["110054301010"] = 101
    cleaned = clean_bps(
        source,
        configuration(),
        province_configuration(),
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="0 sampai 100"):
        validate_bps_value_ranges(cleaned.frame)
