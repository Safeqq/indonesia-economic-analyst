SELECT DISTINCT
    observations.indicator_code,
    observations.observation_date
FROM stg_bps AS observations
WHERE NOT EXISTS (
    SELECT 1
    FROM dim_indicator_metadata_history AS history
    INNER JOIN dim_indicator AS indicator
        ON indicator.indicator_id = history.indicator_id
    INNER JOIN dim_source AS source
        ON source.source_id = history.source_id
    WHERE indicator.indicator_code = observations.indicator_code
      AND source.source_code = observations.source_code
      AND observations.observation_date
          BETWEEN history.period_start AND history.period_end
);

