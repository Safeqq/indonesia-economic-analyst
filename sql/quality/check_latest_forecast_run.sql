SELECT
    i.indicator_code,
    r.region_code,
    fr.selected_model_name,
    fr.baseline_model_name,
    fr.quality_status,
    fr.mae_improvement_percent,
    fr.data_end,
    fr.generated_at
FROM fact_forecast_run AS fr
JOIN dim_indicator AS i ON i.indicator_id = fr.indicator_id
JOIN dim_region AS r ON r.region_id = fr.region_id
WHERE fr.forecast_run_id = (
    SELECT latest.forecast_run_id
    FROM fact_forecast_run AS latest
    WHERE latest.indicator_id = fr.indicator_id
      AND latest.region_id = fr.region_id
      AND latest.source_id = fr.source_id
    ORDER BY latest.generated_at DESC, latest.forecast_run_id DESC
    LIMIT 1
)
ORDER BY i.indicator_code, r.region_code;
