SELECT
    s.source_code,
    MAX(f.ingested_at) AS last_ingested_at,
    TIMESTAMPDIFF(HOUR, MAX(f.ingested_at), CURRENT_TIMESTAMP) AS age_hours
FROM fact_economic_indicator AS f
JOIN dim_source AS s ON s.source_id = f.source_id
GROUP BY s.source_code;
