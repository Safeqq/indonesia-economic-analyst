SELECT
    observation_date,
    COUNT(*) AS duplicate_count
FROM mart_monetary_conditions
GROUP BY observation_date
HAVING COUNT(*) > 1;
