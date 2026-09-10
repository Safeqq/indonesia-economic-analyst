WITH ordered_observations AS (
    SELECT
        indicator_code,
        region_code,
        observation_date,
        LEAD(observation_date) OVER (
            PARTITION BY indicator_code, region_code
            ORDER BY observation_date
        ) AS next_observation_date
    FROM stg_bps
)
SELECT
    indicator_code,
    region_code,
    observation_date AS period_before_gap,
    next_observation_date AS period_after_gap,
    TIMESTAMPDIFF(YEAR, observation_date, next_observation_date) - 1
        AS missing_period_count
FROM ordered_observations
WHERE TIMESTAMPDIFF(YEAR, observation_date, next_observation_date) > 1;

