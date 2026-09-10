-- Grain: satu baris per indikator, negara, dan tanggal observasi.
CREATE OR REPLACE VIEW mart_indicator_trends AS
WITH windowed_observations AS (
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
        LEAD(observation_date) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
        ) AS next_observation_date,
        LEAD(value) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
        ) AS next_value,
        AVG(value) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3_period_average,
        ingested_at
    FROM stg_world_bank
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
    next_observation_date,
    next_value,
    rolling_3_period_average,
    CASE
        WHEN frequency = 'annual'
         AND TIMESTAMPDIFF(
             YEAR, previous_observation_date, observation_date
         ) = 1
        THEN value - previous_value
    END AS yoy_absolute_change,
    CASE
        WHEN frequency = 'annual'
         AND TIMESTAMPDIFF(
             YEAR, previous_observation_date, observation_date
         ) = 1
        THEN 100 * (value - previous_value) / NULLIF(ABS(previous_value), 0)
    END AS yoy_percent_change,
    ingested_at
FROM windowed_observations;
