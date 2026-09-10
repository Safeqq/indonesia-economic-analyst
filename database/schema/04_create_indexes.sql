CREATE INDEX IF NOT EXISTS idx_fact_observation_date
    ON fact_economic_indicator (observation_date);
CREATE INDEX IF NOT EXISTS idx_fact_region_indicator
    ON fact_economic_indicator (region_id, indicator_id);
