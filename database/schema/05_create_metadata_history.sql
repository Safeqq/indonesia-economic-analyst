CREATE TABLE IF NOT EXISTS dim_indicator_metadata_history (
    metadata_version_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    indicator_id INT NOT NULL,
    source_id INT NOT NULL,
    source_variable_id VARCHAR(50) NOT NULL,
    derived_variable_id VARCHAR(50) NOT NULL,
    derived_period_id VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(255) NOT NULL,
    unit VARCHAR(100) NOT NULL,
    definition_text TEXT,
    notes TEXT,
    metadata_hash CHAR(64) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    first_observed_at TIMESTAMP NOT NULL,
    last_observed_at TIMESTAMP NOT NULL,
    UNIQUE KEY uq_indicator_metadata_version
        (indicator_id, source_id, metadata_hash),
    FOREIGN KEY (indicator_id) REFERENCES dim_indicator(indicator_id),
    FOREIGN KEY (source_id) REFERENCES dim_source(source_id)
);
