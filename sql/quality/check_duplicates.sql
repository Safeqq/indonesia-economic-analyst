SELECT
    indicator_id,
    region_id,
    source_id,
    observation_date,
    COUNT(*) AS duplicate_count
FROM fact_economic_indicator
GROUP BY indicator_id, region_id, source_id, observation_date
HAVING COUNT(*) > 1;
