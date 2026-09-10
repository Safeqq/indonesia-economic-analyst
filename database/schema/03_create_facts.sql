CREATE TABLE IF NOT EXISTS fact_economic_indicator (
    observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    indicator_id INT NOT NULL,
    region_id INT NOT NULL,
    source_id INT NOT NULL,
    observation_date DATE NOT NULL,
    value DECIMAL(24, 6) NOT NULL,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_observation (indicator_id, region_id, source_id, observation_date),
    FOREIGN KEY (indicator_id) REFERENCES dim_indicator(indicator_id),
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
    FOREIGN KEY (source_id) REFERENCES dim_source(source_id)
);

CREATE TABLE IF NOT EXISTS fact_pipeline_run (
    run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL,
    status ENUM('running', 'success', 'failed') NOT NULL,
    rows_loaded INT NOT NULL DEFAULT 0,
    error_message TEXT
);
