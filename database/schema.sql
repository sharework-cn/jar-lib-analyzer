-- Source Code Difference Analysis System Database Schema
-- MySQL 8.0+

-- Use existing database
USE jal;

-- Services table
CREATE TABLE services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    ip_address VARCHAR(15),
    port INT,
    username VARCHAR(50),
    password VARCHAR(100),
    server_base_path VARCHAR(500),
    jar_path VARCHAR(500),
    classes_path VARCHAR(500),
    source_path VARCHAR(500),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- JAR files table
CREATE TABLE jar_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    jar_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    last_modified TIMESTAMP,
    is_third_party BOOLEAN DEFAULT FALSE,
    is_latest BOOLEAN DEFAULT FALSE,
    decompile_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uk_service_jar (service_id, jar_name)
);

-- Java source files table
CREATE TABLE java_source_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    jar_file_id INT NULL,
    class_full_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_content LONGTEXT,
    file_size BIGINT,
    last_modified TIMESTAMP,
    is_latest BOOLEAN DEFAULT FALSE,
    file_hash VARCHAR(64),
    line_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (jar_file_id) REFERENCES jar_files(id) ON DELETE SET NULL,
    UNIQUE KEY uk_service_class (service_id, class_full_name)
);

-- Source differences table
CREATE TABLE source_differences (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    java_source_file_id INT NOT NULL,
    difference_type ENUM('added', 'deleted', 'modified') NOT NULL,
    line_number INT,
    old_content TEXT,
    new_content TEXT,
    diff_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE CASCADE
);

-- Performance optimization indexes
CREATE INDEX idx_services_name ON services(service_name);
CREATE INDEX idx_jar_files_service ON jar_files(service_id);
CREATE INDEX idx_jar_files_latest ON jar_files(is_latest);
CREATE INDEX idx_java_source_service ON java_source_files(service_id);
CREATE INDEX idx_java_source_jar ON java_source_files(jar_file_id);
CREATE INDEX idx_java_source_class ON java_source_files(class_full_name);
CREATE INDEX idx_java_source_latest ON java_source_files(is_latest);
CREATE INDEX idx_differences_service ON source_differences(service_id);
CREATE INDEX idx_differences_type ON source_differences(difference_type);

-- Full-text search indexes for content search
CREATE FULLTEXT INDEX idx_java_source_content ON java_source_files(file_content);
CREATE FULLTEXT INDEX idx_java_source_class_name ON java_source_files(class_full_name);
