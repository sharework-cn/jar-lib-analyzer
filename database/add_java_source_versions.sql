-- Add java_source_file_versions table and modify java_source_files table
-- MySQL 8.0+

USE jal;

-- Drop existing foreign key constraints that reference java_source_files
ALTER TABLE class_files DROP FOREIGN KEY class_files_ibfk_2;
ALTER TABLE java_source_in_jar_files DROP FOREIGN KEY java_source_in_jar_files_ibfk_2;
ALTER TABLE source_differences DROP FOREIGN KEY source_differences_ibfk_2;

-- Create java_source_file_versions table
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
    INDEX idx_version (version),
    INDEX idx_file_hash (file_hash),
    INDEX idx_last_modified (last_modified)
);

-- Modify java_source_files table - remove version-specific fields
ALTER TABLE java_source_files 
DROP COLUMN file_path,
DROP COLUMN file_content,
DROP COLUMN file_size,
DROP COLUMN last_modified,
DROP COLUMN file_hash,
DROP COLUMN line_count;

-- Remove unique constraint on class_full_name since it's no longer unique
ALTER TABLE java_source_files DROP INDEX uk_class_name;

-- Add new indexes for java_source_files
CREATE INDEX idx_class_full_name ON java_source_files(class_full_name);

-- Recreate foreign key constraints
ALTER TABLE class_files 
ADD CONSTRAINT class_files_ibfk_2 
FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE SET NULL;

ALTER TABLE java_source_in_jar_files 
ADD CONSTRAINT java_source_in_jar_files_ibfk_2 
FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE CASCADE;

ALTER TABLE source_differences 
ADD CONSTRAINT source_differences_ibfk_2 
FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE CASCADE;

