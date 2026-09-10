SELECT
    r.region_name,
    f.observation_date,
    f.value AS growth_percent,
    LAG(f.value) OVER (
        PARTITION BY f.region_id, f.indicator_id
        ORDER BY f.observation_date
    ) AS previous_period,
    f.value - LAG(f.value) OVER (
        PARTITION BY f.region_id, f.indicator_id
        ORDER BY f.observation_date
    ) AS percentage_point_change
FROM fact_economic_indicator AS f
JOIN dim_region AS r ON r.region_id = f.region_id
JOIN dim_indicator AS i ON i.indicator_id = f.indicator_id
WHERE i.indicator_code = 'NY.GDP.MKTP.KD.ZG'
ORDER BY r.region_name, f.observation_date;
