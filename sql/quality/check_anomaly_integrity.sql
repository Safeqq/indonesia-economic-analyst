SELECT
    anomaly_id,
    observation_date,
    anomaly_type,
    'invalid_anomaly_event' AS violation
FROM fact_anomaly_event
WHERE TRIM(reason) = ''
   OR reason IS NULL
   OR (anomaly_type = 'missing_value' AND observed_value IS NOT NULL)
   OR (anomaly_type <> 'missing_value' AND observed_value IS NULL);
