SELECT
    indicator_code,
    region_code,
    observation_date,
    value,
    CASE
        WHEN indicator_code REGEXP '^BPS[.]543[.]' THEN 'expected 0..100 percent'
        WHEN indicator_code REGEXP '^BPS[.]1975[.]' THEN 'expected value above zero'
    END AS violated_rule
FROM stg_bps
WHERE (indicator_code REGEXP '^BPS[.]543[.]' AND value NOT BETWEEN 0 AND 100)
   OR (indicator_code REGEXP '^BPS[.]1975[.]' AND value <= 0);
