SELECT
    observation_id,
    indicator_code,
    region_code,
    observation_date,
    source_code
FROM stg_world_bank
WHERE indicator_code IS NULL
   OR TRIM(indicator_code) = ''
   OR indicator_name IS NULL
   OR TRIM(indicator_name) = ''
   OR unit IS NULL
   OR TRIM(unit) = ''
   OR frequency IS NULL
   OR region_code IS NULL
   OR TRIM(region_code) = ''
   OR region_name IS NULL
   OR TRIM(region_name) = ''
   OR observation_date IS NULL
   OR value IS NULL
   OR source_code IS NULL
   OR ingested_at IS NULL;
