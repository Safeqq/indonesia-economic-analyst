SELECT
    observation_date,
    COUNT(DISTINCT indicator_code) AS indicator_coverage
FROM stg_bank_indonesia
WHERE region_code = 'IDN'
GROUP BY observation_date
HAVING COUNT(DISTINCT indicator_code) <> 2
    OR SUM(indicator_code = 'BI.POLICY_RATE.MONTHLY') <> 1
    OR SUM(indicator_code = 'BI.JISDOR.USD_IDR.MONTHLY_AVG') <> 1;
