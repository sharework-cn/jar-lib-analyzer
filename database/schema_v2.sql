-- Source Code Difference Analysis System Database Schema V2
-- MySQL 8.0+
-- 基于数据库的Java库分析系统

-- Use existing database

-- 删除旧表（如果存在）
DROP TABLE IF EXISTS source_differences;
DROP TABLE IF EXISTS java_source_files;
DROP TABLE IF EXISTS jar_files;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS class_files;
DROP TABLE IF EXISTS java_source_file_versions;
DROP TABLE IF EXISTS java_source_in_jar_files;

-- Services table - 服务信息表
CREATE TABLE services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_name VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL DEFAULT 'production',
    ip_address VARCHAR(15),
    port INT,
    username VARCHAR(50),
    password VARCHAR(100),
    server_base_path VARCHAR(500),
    jar_path VARCHAR(500),
    classes_path VARCHAR(500),
    source_path VARCHAR(500),
    jar_info_file_path VARCHAR(500) NOT NULL COMMENT 'JAR信息文件路径',
    class_info_file_path VARCHAR(500) NOT NULL COMMENT 'Class信息文件路径',
    jar_decompile_output_dir VARCHAR(500) NOT NULL COMMENT 'JAR反编译输出目录',
    class_decompile_output_dir VARCHAR(500) NOT NULL COMMENT 'Class反编译输出目录',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_service_environment (service_name, environment)
);

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
    version_no INT COMMENT '版本号，基于文件大小变化',
    last_version_no INT COMMENT '最新版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_hash VARCHAR(64) COMMENT '源码内容哈希值',
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uk_service_jar (service_id, jar_name),
    INDEX idx_jar_name (jar_name),
    INDEX idx_version_no (version_no)
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
    version_no INT COMMENT '版本号，基于文件大小变化',
    last_version_no INT COMMENT '最新版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE SET NULL,
    UNIQUE KEY uk_service_class (service_id, class_full_name),
    INDEX idx_class_full_name (class_full_name),
    INDEX idx_version_no (version_no)
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
    compares_to_java_source_file_version_id INT NOT NULL,
    difference_type ENUM('added', 'deleted', 'modified') NOT NULL,
    line_number INT,
    old_content TEXT,
    new_content TEXT,
    diff_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (compares_to_java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE
);

-- Performance optimization indexes
CREATE INDEX idx_services_name ON services(service_name);
CREATE INDEX idx_services_environment ON services(environment);
CREATE INDEX idx_jar_files_service ON jar_files(service_id);
CREATE INDEX idx_jar_files_latest ON jar_files(is_latest);
CREATE INDEX idx_jar_files_third_party ON jar_files(is_third_party);
CREATE INDEX idx_class_files_service ON class_files(service_id);
-- Note: jar_files.jar_name already has INDEX idx_jar_name
-- Note: jar_files.version_no already has INDEX idx_version_no
-- Note: class_files.class_full_name already has INDEX idx_class_full_name
-- Note: class_files.version_no already has INDEX idx_version_no
-- Note: java_source_files.class_full_name already has UNIQUE KEY uk_class_full_name
-- Note: java_source_file_versions.file_hash already has INDEX idx_file_hash
CREATE INDEX idx_jar_source_jar ON java_source_in_jar_files(jar_file_id);
CREATE INDEX idx_jar_source_version ON java_source_in_jar_files(java_source_file_version_id);
CREATE INDEX idx_class_files_source_version ON class_files(java_source_file_version_id);
CREATE INDEX idx_differences_service ON source_differences(service_id);

-- Full-text search indexes for content search
CREATE FULLTEXT INDEX idx_java_source_versions_content ON java_source_file_versions(file_content);
CREATE FULLTEXT INDEX idx_java_source_class_name_fulltext ON java_source_files(class_full_name);
