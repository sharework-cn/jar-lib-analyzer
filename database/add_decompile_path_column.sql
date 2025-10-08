-- Add decompile_path column to jar_files and class_files tables
-- MySQL 8.0+

USE jal;

-- Add decompile_path column to jar_files table
ALTER TABLE jar_files 
ADD COLUMN decompile_path VARCHAR(500) COMMENT 'JAR反编译输出目录路径' AFTER file_path;

-- Add decompile_path column to class_files table  
ALTER TABLE class_files 
ADD COLUMN decompile_path VARCHAR(500) COMMENT 'Class反编译输出目录路径' AFTER file_path;

-- Add indexes for performance
CREATE INDEX idx_jar_files_decompile_path ON jar_files(decompile_path);
CREATE INDEX idx_class_files_decompile_path ON class_files(decompile_path);
