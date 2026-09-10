SELECT
    indicator_code,
    region_code,
    source_code,
    observation_date,
    COUNT(*) AS duplicate_count
FROM stg_bank_indonesia
GROUP BY indicator_code, region_code, source_code, observation_date
HAVING COUNT(*) > 1;
