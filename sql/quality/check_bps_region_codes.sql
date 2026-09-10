SELECT DISTINCT
    region_code,
    region_name,
    region_level,
    parent_region_code
FROM stg_bps
WHERE region_code NOT REGEXP '^[0-9]{4}$'
   OR region_level <> 'province'
   OR parent_region_code IS NULL
   OR parent_region_code <> 'IDN';

