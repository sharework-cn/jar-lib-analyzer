# 基于数据库的Java库分析系统设计文档 V2

## 1. 系统概述

### 1.1 系统目的
本系统是一个基于数据库的Java库分析系统，用于分析、比较和管理不同服务环境中的JAR文件、Class文件和Java源码。系统通过数据库存储所有信息，支持按服务进行批量处理，并提供完整的源码差异分析和版本管理功能。

### 1.2 系统范围
- 服务信息管理和配置
- JAR文件和Class文件信息导入
- 文件反编译和源码提取
- Java源码文件版本管理和关联
- 孤立源码清理
- 源码差异分析和比较
- JAR和Class文件版本管理
- 智能源码合并和去重

### 1.3 核心特性
- **数据库驱动**: 所有数据存储在MySQL数据库中，支持复杂查询和关联
- **按服务处理**: 支持按服务名称和环境进行批量处理
- **版本化管理**: Java源码文件支持版本管理，相同内容自动合并
- **智能过滤**: 支持按服务、JAR、Class名称进行精确过滤
- **自动化流程**: 从文件信息导入到源码分析的完整自动化流程
- **关联管理**: 通过关联表管理JAR文件、Class文件和源码文件的关系
- **数据清理**: 自动清理不再被引用的孤立源码文件
- **进度跟踪**: 使用tqdm提供实时进度条和统计信息
- **Windows兼容**: 支持Windows长路径和路径标准化

## 2. 系统架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   配置管理      │    │   数据处理      │    │   源码分析      │
│                 │    │                 │    │                 │
│ - 服务配置      │───▶│ - 文件导入      │───▶│ - 反编译        │
│ - 环境管理      │    │ - 信息解析      │    │ - 源码提取      │
│ - 路径配置      │    │ - 数据库存储    │    │ - 关联管理      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据库层                                │
│                                                                 │
│ - services (服务信息)                                          │
│ - jar_files (JAR文件信息，支持版本管理)                        │
│ - class_files (Class文件信息，支持版本管理)                    │
│ - java_source_files (Java源码文件)                             │
│ - java_source_file_versions (Java源码文件版本)                 │
│ - java_source_in_jar_files (JAR源码关联)                       │
│ - source_differences (源码差异)                                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 配置管理层
- **服务配置**: JSON格式的服务配置文件，包含连接信息、路径配置等
- **环境管理**: 支持多环境（production、test、dev等）的服务管理
- **路径配置**: 动态路径配置，支持变量替换

#### 2.2.2 数据处理层
- **文件信息导入**: 从服务器或本地文件导入JAR/Class文件信息
- **信息解析**: 解析文件大小、修改时间、依赖关系等信息
- **数据库存储**: 将解析后的信息存储到数据库表中

#### 2.2.3 源码分析层
- **文件反编译**: 使用CFR工具反编译JAR和Class文件
- **源码提取**: 从反编译结果中提取Java源码文件
- **关联管理**: 建立源码文件与原始文件的关联关系

## 3. 数据库设计

### 3.1 表结构设计

#### 3.1.1 services 表
```sql
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
    jar_info_file_path VARCHAR(500) NOT NULL,
    class_info_file_path VARCHAR(500) NOT NULL,
    jar_decompile_output_dir VARCHAR(500) NOT NULL,
    class_decompile_output_dir VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_service_environment (service_name, environment)
);
```

#### 3.1.2 jar_files 表
```sql
CREATE TABLE jar_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    jar_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    last_modified TIMESTAMP,
    is_third_party BOOLEAN DEFAULT FALSE,
    is_latest BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500),
    decompile_path VARCHAR(500),
    version_no INT COMMENT '版本号，基于文件大小变化',
    last_version_no INT COMMENT '最新版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uk_service_jar (service_id, jar_name),
    INDEX idx_jar_name (jar_name),
    INDEX idx_version_no (version_no)
);
```

#### 3.1.3 class_files 表
```sql
CREATE TABLE class_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    service_id INT NOT NULL,
    class_full_name VARCHAR(500) NOT NULL,
    file_size BIGINT,
    last_modified TIMESTAMP,
    file_path VARCHAR(500),
    decompile_path VARCHAR(500),
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
```

#### 3.1.4 java_source_files 表
```sql
CREATE TABLE java_source_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    class_full_name VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_class_full_name (class_full_name)
);
```

#### 3.1.5 java_source_file_versions 表
```sql
CREATE TABLE java_source_file_versions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    java_source_file_id INT NOT NULL,
    version VARCHAR(50) COMMENT '版本号，导入时为空，后续阶段重建',
    file_path VARCHAR(500) NOT NULL,
    file_content LONGTEXT,
    file_size BIGINT,
    last_modified TIMESTAMP,
    file_hash VARCHAR(64),
    line_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (java_source_file_id) REFERENCES java_source_files(id) ON DELETE CASCADE,
    INDEX idx_java_source_file_id (java_source_file_id),
    INDEX idx_file_hash (file_hash)
);
```

#### 3.1.6 关联表
```sql
-- JAR源码关联表（多对多关系）
CREATE TABLE java_source_in_jar_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    jar_file_id INT NOT NULL,
    java_source_file_version_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (jar_file_id) REFERENCES jar_files(id) ON DELETE CASCADE,
    FOREIGN KEY (java_source_file_version_id) REFERENCES java_source_file_versions(id) ON DELETE CASCADE,
    UNIQUE KEY uk_jar_source_version (jar_file_id, java_source_file_version_id)
);
```

注意：Class文件与Java源码文件版本是一对一关系，直接在`class_files`表中通过`java_source_file_version_id`字段关联，无需单独的关联表。

### 3.2 索引设计
- 服务名称和环境组合唯一索引
- JAR文件名和服务组合唯一索引
- Class类名和服务组合唯一索引
- 源码文件类名唯一索引
- JAR文件名独立索引（支持跨服务查询）
- Class类名独立索引（支持跨服务查询）
- 版本号索引（支持版本管理查询）
- 性能优化索引（文件哈希、修改时间等）
- 全文搜索索引（源码内容、类名）

## 4. 处理流程

### 4.1 完整处理流程
```
1. 服务信息导入
   ├── 读取JSON配置文件
   ├── 验证配置信息
   └── 存储到services表

2. JAR文件信息导入
   ├── 从服务器或本地文件获取JAR信息
   ├── 解析文件大小、修改时间等
   ├── 判断第三方依赖
   └── 存储到jar_files表

3. Class文件信息导入
   ├── 从服务器或本地文件获取Class信息
   ├── 解析类名、文件大小等
   └── 存储到class_files表

4. JAR文件反编译
   ├── 下载/复制JAR文件
   ├── 使用CFR工具反编译
   └── 保存到指定输出目录

5. Class文件反编译
   ├── 下载/复制Class文件
   ├── 使用CFR工具反编译
   └── 保存到指定输出目录

6. Java源码导入
   ├── 扫描反编译输出目录
   ├── 提取Java源码文件
   ├── 计算文件哈希和行数
   ├── 存储到java_source_files和java_source_file_versions表
   ├── 建立关联关系
   └── 支持智能过滤和版本管理

7. 孤立源码清理
   ├── 查找未被引用的源码文件
   ├── 删除孤立文件
   └── 更新统计信息
```

### 4.2 按服务处理
系统支持按服务进行批量处理，每个服务可以独立执行完整的处理流程：

```bash
# 处理单个服务
python import_services.py --service-name dsop_gateway
python import_jar_files.py --service-name dsop_gateway
python import_class_files.py --service-name dsop_gateway
python decompile_jar_files.py --service-name dsop_gateway
python decompile_class_files.py --service-name dsop_gateway
python import_java_sources.py --service-name dsop_gateway
python cleanup_orphaned_sources.py --service-name dsop_gateway

# 处理所有服务
python import_services.py --all-services
python import_jar_files.py --all-services
# ... 其他脚本
```

### 4.3 智能过滤和版本管理
系统支持多种过滤模式和版本管理功能：

```bash
# 智能过滤模式
python import_java_sources.py --service-name dsop_core --jar-name specific.jar --dry-run
python import_java_sources.py --service-name dsop_core --class-name com.example.Class --dry-run
python import_java_sources.py --all-services --dry-run

# 版本管理
python manage_versions.py --service-name dsop_core --generate-jar-versions
python manage_versions.py --all-services --generate-class-versions
```

## 5. 脚本工具

### 5.1 服务管理脚本
- **import_services.py**: 导入服务配置信息
- **import_jar_files.py**: 导入JAR文件信息
- **import_class_files.py**: 导入Class文件信息

### 5.2 反编译脚本
- **decompile_jar_files.py**: JAR文件反编译
- **decompile_class_files.py**: Class文件反编译

### 5.3 源码管理脚本
- **import_java_sources.py**: 导入Java源码文件，支持智能过滤和版本管理
- **cleanup_orphaned_sources.py**: 清理孤立源码文件
- **clean_data.py**: 数据清理脚本，支持按外键依赖顺序清理

### 5.4 配置管理
- **JSON配置文件**: 服务配置信息
- **环境变量支持**: 配置路径优先级管理
- **默认配置**: 内置默认配置值

## 6. 数据关联关系

### 6.1 关联图
```
services (服务)
    ├── jar_files (JAR文件，支持版本管理)
    │   └── java_source_in_jar_files (多对多关联)
    │       └── java_source_file_versions (源码版本)
    │           └── java_source_files (源码文件)
    └── class_files (Class文件，支持版本管理)
        └── java_source_file_version_id (直接关联)
            └── java_source_file_versions (源码版本)
                └── java_source_files (源码文件)
```

### 6.2 数据一致性
- 外键约束确保数据完整性
- 级联删除保证数据一致性
- 唯一约束防止重复数据
- 关联表管理多对多关系

## 7. 性能优化

### 7.1 数据库优化
- 合理的索引设计
- 分页查询支持
- 批量操作优化
- 连接池管理

### 7.2 处理优化
- 并行处理支持
- 增量更新机制
- 资源管理

## 8. 扩展性设计

### 8.1 模块化设计
- 独立的脚本模块
- 可配置的处理流程
- 插件化架构支持

### 8.2 多环境支持
- 环境隔离
- 配置分离
- 数据隔离

### 8.3 Web界面和API
- **搜索界面**：支持JAR名称和类名模糊搜索
- **版本历史界面**：展示JAR/Class文件的版本历史
- **差异对比界面**：版本间的源码差异对比
- **REST API接口**：为前端提供数据服务
- **数据库视图**：优化查询性能

## 9. 监控和维护

### 9.1 日志管理
- 结构化日志记录
- 错误追踪和报告
- 性能监控

### 9.2 数据维护
- 定期数据清理
- 备份和恢复
- 数据迁移支持

### 9.3 健康检查
- 数据库连接检查
- 服务状态监控
- 处理进度跟踪

## 10. 版本管理设计

### 10.1 版本管理策略
系统支持基于文件大小的智能版本管理：

#### 10.1.1 JAR文件版本管理
- 按JAR名称分组，跨服务管理版本
- 基于文件大小分配版本号：相同大小 = 相同版本号
- 不同文件大小 = 不同版本号
- 版本号按首次出现的文件大小顺序分配
- 同时自动合并相同版本文件的源码映射关系

#### 10.1.2 Class文件版本管理
- 按类全名分组，跨服务管理版本
- 基于文件大小分配版本号：相同大小 = 相同版本号
- 不同文件大小 = 不同版本号
- 版本号按首次出现的文件大小顺序分配
- 同时自动合并相同版本文件的源码映射关系

### 10.2 源码合并策略
- 相同版本号的JAR/Class文件共享源码版本
- 通过`java_source_file_version_id`关联实现源码复用
- 减少重复存储，提高查询效率
- 版本生成时自动合并源码映射，无需额外遍历

### 10.3 智能过滤系统
系统实现了完整的智能过滤功能：

#### 10.3.1 过滤器架构
- `JavaSourceFilter`类：统一过滤逻辑
- 支持服务级和文件级双重过滤
- 提供dry-run模式预览

#### 10.3.2 过滤参数
- `--service-name`: 指定服务名称
- `--jar-name`: 指定JAR文件名称
- `--class-name`: 指定类全名
- `--all-services`: 处理所有服务
- `--dry-run`: 预览模式，不执行实际导入

#### 10.3.3 过滤逻辑
1. **服务级过滤**: 根据服务名称筛选
2. **文件级过滤**: 根据JAR/Class名称筛选
3. **目录扫描**: 智能识别反编译输出目录
4. **统计输出**: 提供详细的处理统计信息

### 10.4 进度跟踪系统
- 使用`tqdm`库提供实时进度条
- 支持Windows长路径兼容
- 路径标准化（统一使用Linux风格斜杠）
- 固定位置进度条，不随日志滚动

## 11. Web界面设计

### 11.1 搜索界面
- **JAR名称搜索**：支持模糊匹配JAR文件名称
- **类名搜索**：支持模糊匹配类全名
- **搜索结果展示**：显示匹配的JAR包和独立Class文件
- **快速导航**：点击结果直接进入版本历史界面

### 11.2 版本历史界面
- **版本时间线**：按版本号展示时间线
- **版本信息**：每个版本的最早/最晚更新时间
- **服务分布**：使用该版本的服务列表
- **版本对比**：点击版本号查看与上一版本的差异

### 11.3 差异对比界面
- **JAR差异**：展示JAR包内所有源码文件的差异
- **Class差异**：展示单个Class文件的源码差异
- **并排对比**：左右分栏显示版本间差异
- **高亮显示**：新增、删除、修改的代码高亮

### 11.4 API接口设计
```python
# 搜索接口
GET /api/search?q={query}&type={jar|class}
GET /api/jars/{jar_name}/versions
GET /api/classes/{class_name}/versions
GET /api/versions/{version_id}/diff?compare_to={prev_version_id}
```