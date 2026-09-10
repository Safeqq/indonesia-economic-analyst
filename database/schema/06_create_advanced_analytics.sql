CREATE TABLE IF NOT EXISTS fact_forecast_run (
    forecast_run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_key CHAR(64) NOT NULL UNIQUE,
    pipeline_version VARCHAR(50) NOT NULL,
    data_fingerprint CHAR(64) NOT NULL,
    config_fingerprint CHAR(64) NOT NULL,
    indicator_id INT NOT NULL,
    region_id INT NOT NULL,
    source_id INT NOT NULL,
    data_start DATE NOT NULL,
    data_end DATE NOT NULL,
    train_start DATE NOT NULL,
    train_end DATE NOT NULL,
    test_start DATE NOT NULL,
    test_end DATE NOT NULL,
    test_observations SMALLINT NOT NULL,
    selected_model_name VARCHAR(100) NOT NULL,
    selected_model_family ENUM('arima', 'sarima') NOT NULL,
    baseline_model_name VARCHAR(100) NOT NULL,
    selected_mae DECIMAL(24, 8) NOT NULL,
    selected_rmse DECIMAL(24, 8) NOT NULL,
    selected_mape_percent DECIMAL(12, 8) NOT NULL,
    baseline_mae DECIMAL(24, 8) NOT NULL,
    baseline_rmse DECIMAL(24, 8) NOT NULL,
    baseline_mape_percent DECIMAL(12, 8) NOT NULL,
    mae_improvement_percent DECIMAL(12, 8),
    interval_coverage_percent DECIMAL(12, 8),
    forecast_horizon SMALLINT NOT NULL,
    confidence_level DECIMAL(6, 5) NOT NULL,
    quality_status ENUM('passed', 'failed') NOT NULL,
    quality_reasons_json LONGTEXT NOT NULL,
    evaluation_metadata_json LONGTEXT NOT NULL,
    final_model_metadata_json LONGTEXT,
    generated_at DATETIME(6) NOT NULL,
    FOREIGN KEY (indicator_id) REFERENCES dim_indicator(indicator_id),
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
    FOREIGN KEY (source_id) REFERENCES dim_source(source_id),
    CHECK (test_observations > 0),
    CHECK (forecast_horizon > 0),
    CHECK (confidence_level > 0 AND confidence_level < 1)
);

CREATE TABLE IF NOT EXISTS fact_forecast (
    forecast_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    forecast_run_id BIGINT NOT NULL,
    forecast_date DATE NOT NULL,
    point_forecast DECIMAL(24, 6) NOT NULL,
    lower_bound DECIMAL(24, 6) NOT NULL,
    upper_bound DECIMAL(24, 6) NOT NULL,
    is_publishable BOOLEAN NOT NULL DEFAULT FALSE,
    generated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_forecast_run_date (forecast_run_id, forecast_date),
    FOREIGN KEY (forecast_run_id) REFERENCES fact_forecast_run(forecast_run_id),
    CHECK (lower_bound <= point_forecast AND point_forecast <= upper_bound)
);

CREATE TABLE IF NOT EXISTS fact_anomaly_event (
    anomaly_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    forecast_run_id BIGINT NOT NULL,
    observation_date DATE NOT NULL,
    observed_value DECIMAL(24, 6),
    value_change DECIMAL(24, 6),
    anomaly_score DECIMAL(24, 8),
    threshold_value DECIMAL(24, 8) NOT NULL,
    anomaly_type ENUM(
        'missing_value',
        'source_revision',
        'economic_anomaly'
    ) NOT NULL,
    detection_method VARCHAR(100) NOT NULL,
    reason TEXT NOT NULL,
    detected_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_anomaly_run_date_type
        (forecast_run_id, observation_date, anomaly_type, detection_method),
    FOREIGN KEY (forecast_run_id) REFERENCES fact_forecast_run(forecast_run_id),
    CHECK (
        (anomaly_type = 'missing_value' AND observed_value IS NULL)
        OR (anomaly_type <> 'missing_value' AND observed_value IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_forecast_lookup
    ON fact_forecast_run (indicator_id, region_id, quality_status, generated_at);

CREATE INDEX IF NOT EXISTS idx_forecast_date
    ON fact_forecast (forecast_date, is_publishable);

CREATE INDEX IF NOT EXISTS idx_anomaly_lookup
    ON fact_anomaly_event (observation_date, anomaly_type);
