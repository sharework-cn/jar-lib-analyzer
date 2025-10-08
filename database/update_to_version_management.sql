-- Update existing database to version management structure
-- MySQL 8.0+

USE jal;

-- Drop existing foreign key constraints
ALTER TABLE class_files DROP FOREIGN KEY class_files_ibfk_2;
ALTER TABLE java_source_in_jar_files DROP FOREIGN KEY java_source_in_jar_files_ibfk_2;

-- Add java_source_file_versions table if not exists
CREATE TABLE IF NOT EXISTS java_source_file_versions (
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

-- Migrate existing data from java_source_files to java_source_file_versions
INSERT INTO java_source_file_versions (
    java_source_file_id, 
    version, 
    file_path, 
    file_content, 
    file_size, 
    last_modified, 
    file_hash, 
    line_count
)
SELECT 
    id,
    NULL as version,
    file_path,
    file_content,
    file_size,
    last_modified,
    file_hash,
    line_count
FROM java_source_files
WHERE file_path IS NOT NULL;

-- Add new columns to class_files
ALTER TABLE class_files 
ADD COLUMN java_source_file_version_id INT COMMENT '关联的Java源码文件版本ID' AFTER java_source_file_id;

-- Add new columns to java_source_in_jar_files
ALTER TABLE java_source_in_jar_files 
ADD COLUMN java_source_file_version_id INT COMMENT '关联的Java源码文件版本ID' AFTER java_source_file_id;

-- Update class_files to reference the first version of each java_source_file
UPDATE class_files cf
JOIN java_source_file_versions jsv ON cf.java_source_file_id = jsv.java_source_file_id
SET cf.java_source_file_version_id = jsv.id
WHERE cf.java_source_file_id IS NOT NULL;

-- Update java_source_in_jar_files to reference the first version of each java_source_file
UPDATE java_source_in_jar_files jsj
JOIN java_source_file_versions jsv ON jsj.java_source_file_id = jsv.java_source_file_id
SET jsj.java_source_file_version_id = jsv.id
WHERE jsj.java_source_file_id IS NOT NULL;

-- Add foreign key constraints for new columns
ALTER TABLE class_files 
ADD CONSTRAINT class_files_ibfk_3 
FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE SET NULL;

ALTER TABLE java_source_in_jar_files 
ADD CONSTRAINT java_source_in_jar_files_ibfk_3 
FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE;

-- Remove old columns and constraints
ALTER TABLE class_files DROP FOREIGN KEY class_files_ibfk_2;
ALTER TABLE class_files DROP COLUMN java_source_file_id;

ALTER TABLE java_source_in_jar_files DROP FOREIGN KEY java_source_in_jar_files_ibfk_2;
ALTER TABLE java_source_in_jar_files DROP COLUMN java_source_file_id;

-- Remove old columns from java_source_files
ALTER TABLE java_source_files 
DROP COLUMN file_path,
DROP COLUMN file_content,
DROP COLUMN file_size,
DROP COLUMN last_modified,
DROP COLUMN file_hash,
DROP COLUMN line_count;

-- Remove unique constraint on class_full_name
ALTER TABLE java_source_files DROP INDEX uk_class_name;

-- Add new indexes
CREATE INDEX idx_class_files_source_version ON class_files(java_source_file_version_id);
CREATE INDEX idx_jar_source_version ON java_source_in_jar_files(java_source_file_version_id);
-- Note: java_source_file_versions.file_hash already has INDEX idx_file_hash

-- Update full-text search index
DROP INDEX idx_java_source_content ON java_source_files;
CREATE FULLTEXT INDEX idx_java_source_versions_content ON java_source_file_versions(file_content);
