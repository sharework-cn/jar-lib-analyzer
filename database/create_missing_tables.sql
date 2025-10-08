-- Create missing class_files table
CREATE TABLE class_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    class_full_name VARCHAR(500) NOT NULL COMMENT '完整类名（包含包名）',
    file_size BIGINT,
    last_modified TIMESTAMP,
    file_path VARCHAR(500) COMMENT 'Class文件本地路径',
    java_source_file_id INT COMMENT '关联的Java源码文件ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE SET NULL,
    UNIQUE KEY uk_service_class (service_id, class_full_name)
);

-- Create missing indexes
CREATE INDEX idx_class_files_service ON class_files(service_id);
CREATE INDEX idx_class_files_class_name ON class_files(class_full_name);
CREATE INDEX idx_class_files_source ON class_files(java_source_file_id);
