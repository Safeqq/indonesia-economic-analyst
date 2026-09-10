SELECT
    observation_id,
    indicator_code,
    region_code,
    observation_date
FROM stg_bank_indonesia
WHERE indicator_code IS NULL
   OR TRIM(indicator_code) = ''
   OR indicator_name IS NULL
   OR TRIM(indicator_name) = ''
   OR unit IS NULL
   OR TRIM(unit) = ''
   OR frequency <> 'monthly'
   OR region_code <> 'IDN'
   OR region_level <> 'country'
   OR observation_date IS NULL
   OR DAY(observation_date) <> 1
   OR value IS NULL;
