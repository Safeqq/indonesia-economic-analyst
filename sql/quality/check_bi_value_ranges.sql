SELECT
    indicator_code,
    observation_date,
    value,
    'outside expected range' AS issue
FROM stg_bank_indonesia
WHERE (
        indicator_code = 'BI.POLICY_RATE.MONTHLY'
        AND (value < 0 OR value > 100)
    )
   OR (
        indicator_code = 'BI.JISDOR.USD_IDR.MONTHLY_AVG'
        AND (value < 1 OR value > 1000000)
    )
   OR indicator_code NOT IN (
        'BI.POLICY_RATE.MONTHLY',
        'BI.JISDOR.USD_IDR.MONTHLY_AVG'
    );
