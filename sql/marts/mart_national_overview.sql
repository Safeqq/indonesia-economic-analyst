-- Grain: satu baris per tahun untuk Indonesia.
CREATE OR REPLACE VIEW mart_national_overview AS
WITH indonesia_observations AS (
    SELECT
        region_code,
        region_name,
        observation_date,
        observation_year,
        indicator_code,
        value,
        ingested_at
    FROM stg_world_bank
    WHERE region_code = 'IDN'
      AND region_level = 'country'
)
SELECT
    region_code,
    region_name,
    observation_date,
    observation_year,
    MAX(CASE
        WHEN indicator_code = 'NY.GDP.MKTP.KD.ZG' THEN value
    END) AS gdp_growth_percent,
    MAX(CASE
        WHEN indicator_code = 'FP.CPI.TOTL.ZG' THEN value
    END) AS inflation_percent,
    MAX(CASE
        WHEN indicator_code = 'SL.UEM.TOTL.ZS' THEN value
    END) AS unemployment_percent,
    MAX(CASE
        WHEN indicator_code = 'SP.POP.TOTL' THEN value
    END) AS population,
    MAX(CASE
        WHEN indicator_code = 'NY.GDP.PCAP.CD' THEN value
    END) AS gdp_per_capita_current_usd,
    COUNT(DISTINCT indicator_code) AS indicator_coverage,
    MAX(ingested_at) AS last_ingested_at
FROM indonesia_observations
GROUP BY
    region_code,
    region_name,
    observation_date,
    observation_year;
