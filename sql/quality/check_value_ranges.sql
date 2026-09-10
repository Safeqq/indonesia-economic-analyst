SELECT
    indicator_code,
    region_code,
    observation_date,
    value,
    CASE
        WHEN indicator_code = 'SL.UEM.TOTL.ZS' THEN 'expected 0..100 percent'
        WHEN indicator_code = 'SP.POP.TOTL' THEN 'expected value above zero'
        WHEN indicator_code = 'NY.GDP.PCAP.CD' THEN 'expected non-negative value'
        WHEN indicator_code = 'NY.GDP.MKTP.KD.ZG' THEN 'expected -100..100 percent'
        WHEN indicator_code = 'FP.CPI.TOTL.ZG' THEN 'expected -100..1000 percent'
    END AS violated_rule
FROM stg_world_bank
WHERE (indicator_code = 'SL.UEM.TOTL.ZS' AND value NOT BETWEEN 0 AND 100)
   OR (indicator_code = 'SP.POP.TOTL' AND value <= 0)
   OR (indicator_code = 'NY.GDP.PCAP.CD' AND value < 0)
   OR (indicator_code = 'NY.GDP.MKTP.KD.ZG' AND value NOT BETWEEN -100 AND 100)
   OR (indicator_code = 'FP.CPI.TOTL.ZG' AND value NOT BETWEEN -100 AND 1000);
