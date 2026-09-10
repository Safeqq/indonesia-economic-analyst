SELECT
    indicator_code,
    region_code,
    observation_date,
    COUNT(*) AS duplicate_count
FROM mart_indicator_trends
GROUP BY indicator_code, region_code, observation_date
HAVING COUNT(*) > 1;
