SELECT
    indicator_code,
    region_code,
    source_code,
    observation_date,
    COUNT(*) AS duplicate_count
FROM stg_bps
GROUP BY indicator_code, region_code, source_code, observation_date
HAVING COUNT(*) > 1;

