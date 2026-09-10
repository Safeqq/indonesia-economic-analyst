WITH ordered_observations AS (
    SELECT
        indicator_code,
        observation_date,
        LEAD(observation_date) OVER (
            PARTITION BY indicator_code
            ORDER BY observation_date
        ) AS next_observation_date
    FROM stg_bank_indonesia
)
SELECT
    indicator_code,
    observation_date,
    next_observation_date,
    TIMESTAMPDIFF(MONTH, observation_date, next_observation_date) AS month_gap
FROM ordered_observations
WHERE TIMESTAMPDIFF(MONTH, observation_date, next_observation_date) > 1;
