SELECT
    f.forecast_run_id,
    f.forecast_date,
    'forecast_bounds_invalid' AS violation
FROM fact_forecast AS f
WHERE f.lower_bound > f.point_forecast
   OR f.point_forecast > f.upper_bound

UNION ALL

SELECT
    f.forecast_run_id,
    f.forecast_date,
    'forecast_not_in_future' AS violation
FROM fact_forecast AS f
JOIN fact_forecast_run AS r ON r.forecast_run_id = f.forecast_run_id
WHERE f.forecast_date <= r.data_end

UNION ALL

SELECT
    f.forecast_run_id,
    f.forecast_date,
    'failed_gate_has_forecast' AS violation
FROM fact_forecast AS f
JOIN fact_forecast_run AS r ON r.forecast_run_id = f.forecast_run_id
WHERE r.quality_status <> 'passed'
   OR f.is_publishable <> 1

UNION ALL

SELECT
    r.forecast_run_id,
    NULL AS forecast_date,
    'passed_gate_wrong_horizon' AS violation
FROM fact_forecast_run AS r
LEFT JOIN fact_forecast AS f ON f.forecast_run_id = r.forecast_run_id
WHERE r.quality_status = 'passed'
GROUP BY r.forecast_run_id, r.forecast_horizon
HAVING COUNT(f.forecast_id) <> r.forecast_horizon;
