-- Grain: satu baris per seri BPS, provinsi, sumber, dan tanggal observasi.
CREATE OR REPLACE VIEW stg_bps AS
SELECT
    f.observation_id,
    i.indicator_code,
    i.indicator_name,
    i.unit,
    i.frequency,
    r.region_code,
    r.region_name,
    r.region_level,
    r.parent_region_code,
    d.date_id,
    d.full_date AS observation_date,
    d.year AS observation_year,
    d.quarter AS observation_quarter,
    d.month AS observation_month,
    f.value,
    s.source_code,
    s.source_name,
    s.source_url,
    f.ingested_at
FROM fact_economic_indicator AS f
INNER JOIN dim_indicator AS i
    ON i.indicator_id = f.indicator_id
INNER JOIN dim_region AS r
    ON r.region_id = f.region_id
INNER JOIN dim_source AS s
    ON s.source_id = f.source_id
INNER JOIN dim_date AS d
    ON d.full_date = f.observation_date
WHERE s.source_code = 'bps';

