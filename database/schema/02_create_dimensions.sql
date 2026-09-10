CREATE TABLE IF NOT EXISTS dim_source (
    source_id INT AUTO_INCREMENT PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL UNIQUE,
    source_name VARCHAR(150) NOT NULL,
    source_url VARCHAR(500) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_indicator (
    indicator_id INT AUTO_INCREMENT PRIMARY KEY,
    indicator_code VARCHAR(100) NOT NULL UNIQUE,
    indicator_name VARCHAR(255) NOT NULL,
    unit VARCHAR(100),
    frequency ENUM('daily', 'monthly', 'quarterly', 'annual') NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_region (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(150) NOT NULL,
    region_level ENUM('country', 'province', 'city') NOT NULL,
    parent_region_code VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year SMALLINT NOT NULL,
    quarter TINYINT NOT NULL,
    month TINYINT NOT NULL
);
