-- Recreate all tables except services table
-- MySQL 8.0+

USE jal;

-- Drop all tables except services
DROP TABLE IF EXISTS source_differences;
DROP TABLE IF EXISTS java_source_in_jar_files;
DROP TABLE IF EXISTS java_source_file_versions;
DROP TABLE IF EXISTS java_source_files;
DROP TABLE IF EXISTS class_files;
DROP TABLE IF EXISTS jar_files;

-- JAR files table - JAR文件信息表
CREATE TABLE jar_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    jar_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    last_modified TIMESTAMP,
    is_third_party BOOLEAN DEFAULT FALSE,
    is_latest BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500) COMMENT 'JAR文件本地路径',
    decompile_path VARCHAR(500) COMMENT 'JAR反编译输出目录路径',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uk_service_jar (service_id, jar_name)
);

-- Class files table - Class文件信息表
CREATE TABLE class_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    class_full_name VARCHAR(500) NOT NULL COMMENT '完整类名（包含包名）',
    file_size BIGINT,
    last_modified TIMESTAMP,
    file_path VARCHAR(500) COMMENT 'Class文件本地路径',
    decompile_path VARCHAR(500) COMMENT 'Class反编译输出目录路径',
    java_source_file_version_id INT COMMENT '关联的Java源码文件版本ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uk_service_class (service_id, class_full_name)
);

-- Java source files table - Java源码文件表
CREATE TABLE java_source_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    class_full_name VARCHAR(500) NOT NULL COMMENT '完整类名（包含包名）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_class_full_name (class_full_name)
);

-- Java source file versions table - Java源码文件版本表
CREATE TABLE java_source_file_versions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    java_source_file_id INT NOT NULL,
    version VARCHAR(50) COMMENT '版本号，导入时为空，后续阶段重建',
    file_path VARCHAR(500) NOT NULL COMMENT '源码文件路径',
    file_content LONGTEXT COMMENT '源码内容',
    file_size BIGINT,
    last_modified TIMESTAMP,
    file_hash VARCHAR(64) COMMENT '文件内容哈希值',
    line_count INT COMMENT '代码行数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE CASCADE,
    INDEX idx_java_source_file_id (java_source_file_id),
    INDEX idx_file_hash (file_hash)
);

-- JAR source mapping table - JAR源码关联表
CREATE TABLE java_source_in_jar_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    jar_file_id INT NOT NULL,
    java_source_file_version_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (jar_file_id) REFERENCES jar_files(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE,
    UNIQUE KEY uk_jar_source_version (jar_file_id, java_source_file_version_id)
);

-- Source differences table - 源码差异表
CREATE TABLE source_differences (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    java_source_file_version_id INT NOT NULL,
    difference_type ENUM('added', 'deleted', 'modified') NOT NULL,
    line_number INT,
    old_content TEXT,
    new_content TEXT,
    diff_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE
);

-- Add foreign key constraint for class_files
ALTER TABLE class_files 
ADD CONSTRAINT class_files_ibfk_2 
FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE SET NULL;

-- Performance optimization indexes
CREATE INDEX idx_jar_files_service ON jar_files(service_id);
CREATE INDEX idx_jar_files_latest ON jar_files(is_latest);
CREATE INDEX idx_jar_files_third_party ON jar_files(is_third_party);
CREATE INDEX idx_class_files_service ON class_files(service_id);
CREATE INDEX idx_class_files_class_name ON class_files(class_full_name);
CREATE INDEX idx_jar_source_jar ON java_source_in_jar_files(jar_file_id);
CREATE INDEX idx_jar_source_version ON java_source_in_jar_files(java_source_file_version_id);
CREATE INDEX idx_class_files_source_version ON class_files(java_source_file_version_id);
CREATE INDEX idx_differences_service ON source_differences(service_id);
CREATE INDEX idx_differences_type ON source_differences(difference_type);

-- Full-text search indexes for content search
CREATE FULLTEXT INDEX idx_java_source_versions_content ON java_source_file_versions(file_content);
CREATE FULLTEXT INDEX idx_java_source_class_name_fulltext ON java_source_files(class_full_name);
