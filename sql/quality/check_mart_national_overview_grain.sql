SELECT
    region_code,
    observation_date,
    COUNT(*) AS duplicate_count
FROM mart_national_overview
GROUP BY region_code, observation_date
HAVING COUNT(*) > 1;
