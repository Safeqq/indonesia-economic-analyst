CREATE TABLE IF NOT EXISTS data_freshness_alert (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_key CHAR(64) NOT NULL UNIQUE,
    source_code VARCHAR(50) NOT NULL,
    alert_type ENUM(
        'missing_successful_run',
        'missing_observations',
        'stale_ingestion',
        'stale_observation'
    ) NOT NULL,
    severity ENUM('warning', 'critical') NOT NULL,
    message TEXT NOT NULL,
    last_success_at DATETIME NULL,
    last_ingested_at DATETIME NULL,
    latest_observation_date DATE NULL,
    first_detected_at DATETIME NOT NULL,
    last_detected_at DATETIME NOT NULL,
    resolved_at DATETIME NULL,
    INDEX idx_freshness_alert_open (source_code, resolved_at, last_detected_at)
);

CREATE TABLE IF NOT EXISTS pipeline_schedule_run (
    schedule_run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL,
    scheduled_period DATE NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    status ENUM('running', 'success', 'failed') NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0,
    rows_loaded INT NOT NULL DEFAULT 0,
    error_message TEXT,
    UNIQUE KEY uq_pipeline_schedule_period (source_code, scheduled_period),
    INDEX idx_pipeline_schedule_status (status, started_at)
);
