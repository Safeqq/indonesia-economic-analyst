SET time_zone = 'SYSTEM';

SET @iei_legacy_timezone_offset_seconds =
    TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW());

SET time_zone = '+00:00';

UPDATE fact_economic_indicator
SET ingested_at = TIMESTAMPADD(
    SECOND,
    @iei_legacy_timezone_offset_seconds,
    ingested_at
)
WHERE @iei_legacy_timezone_offset_seconds <> 0;

UPDATE fact_pipeline_run
SET started_at = TIMESTAMPADD(
        SECOND,
        @iei_legacy_timezone_offset_seconds,
        started_at
    ),
    completed_at = TIMESTAMPADD(
        SECOND,
        @iei_legacy_timezone_offset_seconds,
        completed_at
    )
WHERE @iei_legacy_timezone_offset_seconds <> 0;

UPDATE dim_indicator_metadata_history
SET first_observed_at = TIMESTAMPADD(
        SECOND,
        @iei_legacy_timezone_offset_seconds,
        first_observed_at
    ),
    last_observed_at = TIMESTAMPADD(
        SECOND,
        @iei_legacy_timezone_offset_seconds,
        last_observed_at
    )
WHERE @iei_legacy_timezone_offset_seconds <> 0;
