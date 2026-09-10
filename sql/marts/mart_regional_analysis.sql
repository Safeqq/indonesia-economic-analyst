-- Grain: satu baris per seri BPS, provinsi, dan tanggal observasi.
CREATE OR REPLACE VIEW mart_regional_analysis AS
WITH windowed AS (
    SELECT
        indicator_code,
        indicator_name,
        unit,
        frequency,
        region_code,
        region_name,
        observation_date,
        observation_year,
        value,
        LAG(observation_date) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
        ) AS previous_observation_date,
        LAG(value) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
        ) AS previous_value,
        AVG(value) OVER (
            PARTITION BY indicator_code, observation_date
        ) AS province_average,
        COUNT(*) OVER (
            PARTITION BY indicator_code, observation_date
        ) AS province_coverage,
        RANK() OVER (
            PARTITION BY indicator_code, observation_date
            ORDER BY value DESC
        ) AS value_rank_desc,
        PERCENT_RANK() OVER (
            PARTITION BY indicator_code, observation_date
            ORDER BY value
        ) AS value_percentile,
        ingested_at
    FROM stg_bps
)
SELECT
    indicator_code,
    indicator_name,
    unit,
    frequency,
    region_code,
    region_name,
    observation_date,
    observation_year,
    value,
    previous_observation_date,
    previous_value,
    CASE
        WHEN TIMESTAMPDIFF(
            YEAR, previous_observation_date, observation_date
        ) = 1
        THEN value - previous_value
    END AS yoy_absolute_change,
    CASE
        WHEN TIMESTAMPDIFF(
            YEAR, previous_observation_date, observation_date
        ) = 1
        THEN 100 * (value - previous_value) / NULLIF(ABS(previous_value), 0)
    END AS yoy_percent_change,
    province_average,
    value - province_average AS difference_from_province_average,
    province_coverage,
    value_rank_desc,
    value_percentile,
    ingested_at
FROM windowed;

