CREATE INDEX IF NOT EXISTS idx_fact_observation_date
    ON fact_economic_indicator (observation_date);
CREATE INDEX IF NOT EXISTS idx_fact_region_indicator
    ON fact_economic_indicator (region_id, indicator_id);

CREATE INDEX IF NOT EXISTS idx_indicator_metadata_period
    ON dim_indicator_metadata_history (indicator_id, period_start, period_end);
