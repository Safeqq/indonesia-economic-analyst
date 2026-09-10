-- Grain: satu baris per indikator, anggota ASEAN saat ini, dan tanggal observasi.
CREATE OR REPLACE VIEW mart_asean_comparison AS
WITH asean_members AS (
    SELECT 'BRN' AS region_code, DATE '1984-01-07' AS member_since
    UNION ALL SELECT 'KHM', DATE '1999-04-30'
    UNION ALL SELECT 'IDN', DATE '1967-08-08'
    UNION ALL SELECT 'LAO', DATE '1997-07-23'
    UNION ALL SELECT 'MYS', DATE '1967-08-08'
    UNION ALL SELECT 'MMR', DATE '1997-07-23'
    UNION ALL SELECT 'PHL', DATE '1967-08-08'
    UNION ALL SELECT 'SGP', DATE '1967-08-08'
    UNION ALL SELECT 'THA', DATE '1967-08-08'
    UNION ALL SELECT 'TLS', DATE '2025-10-26'
    UNION ALL SELECT 'VNM', DATE '1995-07-28'
), asean_observations AS (
    SELECT
        source.indicator_code,
        source.indicator_name,
        source.unit,
        source.frequency,
        source.region_code,
        source.region_name,
        members.member_since,
        source.observation_date,
        source.observation_year,
        source.value,
        source.ingested_at
    FROM stg_world_bank AS source
    INNER JOIN asean_members AS members
        ON members.region_code = source.region_code
), ranked_observations AS (
    SELECT
        indicator_code,
        indicator_name,
        unit,
        frequency,
        region_code,
        region_name,
        member_since,
        observation_date,
        observation_year,
        value,
        AVG(value) OVER (
            PARTITION BY indicator_code, observation_date
        ) AS asean_average,
        COUNT(*) OVER (
            PARTITION BY indicator_code, observation_date
        ) AS country_coverage,
        RANK() OVER (
            PARTITION BY indicator_code, observation_date
            ORDER BY value DESC
        ) AS value_rank_desc,
        PERCENT_RANK() OVER (
            PARTITION BY indicator_code, observation_date
            ORDER BY value
        ) AS value_percentile,
        ingested_at
    FROM asean_observations
)
SELECT
    indicator_code,
    indicator_name,
    unit,
    frequency,
    region_code,
    region_name,
    member_since,
    CASE
        WHEN observation_date >= member_since THEN 1
        ELSE 0
    END AS was_member_during_period,
    observation_date,
    observation_year,
    value,
    asean_average,
    value - asean_average AS difference_from_asean_average,
    country_coverage,
    value_rank_desc,
    value_percentile,
    ingested_at
FROM ranked_observations;
