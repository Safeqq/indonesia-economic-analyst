-- Grain: satu bulan kalender untuk kondisi moneter Indonesia.
CREATE OR REPLACE VIEW mart_monetary_conditions AS
WITH monthly_indicators AS (
    SELECT
        observation_date,
        observation_year,
        observation_quarter,
        observation_month,
        MAX(
            CASE
                WHEN indicator_code = 'BI.POLICY_RATE.MONTHLY' THEN value
            END
        ) AS bi_rate_percent,
        MAX(
            CASE
                WHEN indicator_code = 'BI.JISDOR.USD_IDR.MONTHLY_AVG' THEN value
            END
        ) AS jisdor_idr_per_usd,
        COUNT(DISTINCT indicator_code) AS indicator_coverage,
        MAX(ingested_at) AS ingested_at
    FROM stg_bank_indonesia
    WHERE region_code = 'IDN'
      AND frequency = 'monthly'
      AND indicator_code IN (
          'BI.POLICY_RATE.MONTHLY',
          'BI.JISDOR.USD_IDR.MONTHLY_AVG'
      )
    GROUP BY
        observation_date,
        observation_year,
        observation_quarter,
        observation_month
), windowed_conditions AS (
    SELECT
        observation_date,
        observation_year,
        observation_quarter,
        observation_month,
        bi_rate_percent,
        jisdor_idr_per_usd,
        indicator_coverage,
        LAG(bi_rate_percent) OVER (
            ORDER BY observation_date
        ) AS previous_bi_rate_percent,
        LAG(jisdor_idr_per_usd) OVER (
            ORDER BY observation_date
        ) AS previous_jisdor_idr_per_usd,
        AVG(jisdor_idr_per_usd) OVER (
            ORDER BY observation_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS jisdor_rolling_3_month_average,
        ingested_at
    FROM monthly_indicators
)
SELECT
    observation_date,
    observation_year,
    observation_quarter,
    observation_month,
    bi_rate_percent,
    bi_rate_percent - previous_bi_rate_percent AS bi_rate_change_pp,
    jisdor_idr_per_usd,
    jisdor_idr_per_usd - previous_jisdor_idr_per_usd AS jisdor_mom_change,
    100 * (jisdor_idr_per_usd - previous_jisdor_idr_per_usd)
        / NULLIF(ABS(previous_jisdor_idr_per_usd), 0) AS jisdor_mom_percent_change,
    jisdor_rolling_3_month_average,
    indicator_coverage,
    ingested_at
FROM windowed_conditions;
