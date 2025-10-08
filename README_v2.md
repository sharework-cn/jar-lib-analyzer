# 基于数据库的Java库分析系统 V2

一个基于数据库的Java库分析工具集，用于分析、比较和管理不同服务环境中的JAR文件、Class文件和Java源码。系统通过数据库存储所有信息，支持按服务进行批量处理，并提供完整的源码差异分析功能。

## 系统背景

在我们的平台部署过程中，更新不是以全量部署的方式进行的。在更新过程中，某些服务的JAR包可能没有及时更新。这产生了以下需求：

1. **识别过时的JAR包**: 确定哪些服务包含不是最新版本的JAR包
2. **比较差异**: 分析不同服务间JAR包的具体差异
3. **确保一致性**: 维护平台中所有服务的版本一致性
4. **源码级分析**: 提供源码级别的差异分析和比较

本系统通过提供基于数据库的全面分析和比较功能，满足跨多个服务和服务器的JAR包版本管理需求。

## 系统特性

- **数据库驱动**: 所有数据存储在MySQL数据库中，支持复杂查询和关联
- **按服务处理**: 支持按服务名称和环境进行批量处理
- **自动化流程**: 从文件信息导入到源码分析的完整自动化流程
- **关联管理**: 通过关联表管理JAR文件、Class文件和源码文件的关系
- **数据清理**: 自动清理不再被引用的孤立源码文件
- **多环境支持**: 支持生产、测试、开发等多环境管理
- **配置管理**: JSON格式的服务配置文件，支持环境变量和默认配置

## 系统架构

### 数据库设计

系统使用MySQL数据库存储所有信息，主要表结构包括：

- **services**: 服务信息表，存储服务配置和连接信息
- **jar_files**: JAR文件信息表，存储JAR文件元数据
- **class_files**: Class文件信息表，存储Class文件元数据
- **java_source_files**: Java源码文件表，存储反编译后的源码
- **java_source_in_jar_files**: JAR源码关联表，管理JAR文件与源码的多对多关系
- **source_differences**: 源码差异表，存储版本间的差异信息

### 处理流程

```
1. 服务信息导入 → 2. JAR文件信息导入 → 3. Class文件信息导入
                                        ↓
7. 孤立源码清理 ← 6. Java源码导入 ← 5. Class文件反编译 ← 4. JAR文件反编译
```

## 工具组件

### 1. 服务管理脚本

#### 1.1 import_services.py - 服务信息导入

从JSON配置文件导入服务信息到数据库。

**特性:**
- 支持JSON格式配置文件
- 环境变量和命令行参数优先级管理
- 服务+环境唯一性约束
- 支持服务过滤和环境过滤

**使用方法:**
```bash
# 创建示例配置文件
python import_services.py --create-sample work/prod/services_config.json

# 导入所有服务
python import_services.py --config-file work/prod/services_config.json

# 导入特定服务
python import_services.py --service-name dsop_gateway

# 导入特定环境
python import_services.py --environment production
```

**配置文件格式:**
```json
{
  "services": [
    {
      "service_name": "dsop_gateway",
      "environment": "production",
      "ip_address": "10.20.151.32",
      "port": 22,
      "username": "",
      "password": "",
      "server_base_path": "/app/apprun/tomcat_server/webapps/dsop_gateway/WEB-INF",
      "jar_path": "work/prod/lib-download/{service_name}{server_base_path}/lib",
      "classes_path": "work/prod/classes-download/{service_name}{server_base_path}/classes",
      "jar_info_file_path": "work/prod/lib-list/dsop_gateway.txt",
      "class_info_file_path": "work/prod/classes-list/dsop_gateway.txt",
      "jar_decompile_output_dir": "work/prod/lib-decompile",
      "class_decompile_output_dir": "work/prod/classes-decompile",
      "description": "DSOP Gateway Service"
    }
  ]
}
```

#### 1.2 import_jar_files.py - JAR文件信息导入

从服务器或本地文件导入JAR文件信息到数据库。

**特性:**
- 支持从服务器SSH获取文件信息
- 支持从本地文件读取信息
- 自动识别第三方依赖
- 文件大小和修改时间解析

**使用方法:**
```bash
# 导入所有服务的JAR文件信息
python import_jar_files.py --all-services

# 导入特定服务的JAR文件信息
python import_jar_files.py --service-name dsop_gateway

# 指定环境
python import_jar_files.py --service-name dsop_gateway --environment production
```

#### 1.3 import_class_files.py - Class文件信息导入

从服务器或本地文件导入Class文件信息到数据库。

**特性:**
- 支持从服务器SSH获取Class文件信息
- 支持从本地文件读取信息
- 自动提取完整类名
- 文件大小和修改时间解析

**使用方法:**
```bash
# 导入所有服务的Class文件信息
python import_class_files.py --all-services

# 导入特定服务的Class文件信息
python import_class_files.py --service-name dsop_gateway
```

### 2. 反编译脚本

#### 2.1 decompile_jar_files.py - JAR文件反编译

使用CFR工具反编译JAR文件。

**特性:**
- 支持从服务器下载JAR文件
- 支持从本地目录复制JAR文件
- 使用CFR工具进行反编译
- 按服务和时间戳组织输出目录

**使用方法:**
```bash
# 反编译所有服务的JAR文件
python decompile_jar_files.py --all-services

# 反编译特定服务的JAR文件
python decompile_jar_files.py --service-name dsop_gateway
```

#### 2.2 decompile_class_files.py - Class文件反编译

使用CFR工具反编译Class文件。

**特性:**
- 支持从服务器下载Class文件
- 支持从本地目录复制Class文件
- 使用CFR工具进行反编译
- 按类名和时间戳组织输出目录

**使用方法:**
```bash
# 反编译所有服务的Class文件
python decompile_class_files.py --all-services

# 反编译特定服务的Class文件
python decompile_class_files.py --service-name dsop_gateway
```

### 3. 源码管理脚本

#### 3.1 import_java_sources.py - Java源码导入

从反编译输出目录导入Java源码文件到数据库。

**特性:**
- 扫描反编译输出目录
- 提取Java源码文件内容
- 计算文件哈希和行数
- 建立JAR文件和Class文件与源码的关联关系

**使用方法:**
```bash
# 导入所有服务的Java源码
python import_java_sources.py --all-services

# 导入特定服务的Java源码
python import_java_sources.py --service-name dsop_gateway
```

#### 3.2 cleanup_orphaned_sources.py - 孤立源码清理

清理不再被引用的孤立Java源码文件。

**特性:**
- 查找未被JAR文件或Class文件引用的源码
- 支持干运行模式
- 提供清理统计信息
- 支持按服务清理

**使用方法:**
```bash
# 查看清理统计信息
python cleanup_orphaned_sources.py --statistics

# 干运行模式（默认）
python cleanup_orphaned_sources.py --all-services

# 实际执行清理
python cleanup_orphaned_sources.py --all-services --execute

# 清理特定服务
python cleanup_orphaned_sources.py --service-name dsop_gateway --execute
```

## 完整工作流程

### 按服务处理流程

```bash
# 1. 导入服务配置
python import_services.py --service-name dsop_gateway

# 2. 导入JAR文件信息
python import_jar_files.py --service-name dsop_gateway

# 3. 导入Class文件信息
python import_class_files.py --service-name dsop_gateway

# 4. 反编译JAR文件
python decompile_jar_files.py --service-name dsop_gateway

# 5. 反编译Class文件
python decompile_class_files.py --service-name dsop_gateway

# 6. 导入Java源码
python import_java_sources.py --service-name dsop_gateway

# 7. 清理孤立源码
python cleanup_orphaned_sources.py --service-name dsop_gateway --execute
```

### 批量处理流程

```bash
# 处理所有服务
python import_services.py --all-services
python import_jar_files.py --all-services
python import_class_files.py --all-services
python decompile_jar_files.py --all-services
python decompile_class_files.py --all-services
python import_java_sources.py --all-services
python cleanup_orphaned_sources.py --all-services --execute
```

## 环境要求

### 系统要求
- Python 3.7+
- MySQL 8.0+
- Java 8+ (用于CFR反编译工具)

### Python依赖
```
fastapi
sqlalchemy
pandas
paramiko
scp
pymysql
```

### 安装依赖
```bash
pip install -r backend/requirements.txt
```

## 配置说明

### 数据库配置
```bash
# 环境变量
export DATABASE_URL="mysql+pymysql://username:password@host:port/database"

# 或使用默认配置
# mysql+pymysql://jal:271828@172.30.80.95:32306/jal
```

### 服务配置
服务配置支持以下优先级：
1. 命令行参数
2. 环境变量
3. 默认值

```bash
# 环境变量配置
export SERVICE_CONFIG_FILE="work/prod/services_config.json"
```

## 目录结构

```
java-lib-analyzer/
├── backend/                    # 后端代码
│   ├── main.py                # FastAPI主程序
│   ├── requirements.txt       # Python依赖
│   └── scripts/               # 处理脚本
│       ├── import_services.py
│       ├── import_jar_files.py
│       ├── import_class_files.py
│       ├── decompile_jar_files.py
│       ├── decompile_class_files.py
│       ├── import_java_sources.py
│       └── cleanup_orphaned_sources.py
├── database/                   # 数据库相关
│   ├── schema.sql            # 原始数据库结构
│   └── schema_v2.sql         # V2数据库结构
├── docs/                      # 文档
│   ├── system_design_v2.md   # 系统设计文档
│   └── introduce_to_source_code_difference_analysis.md
├── assets/                    # 资源文件
│   └── jar/
│       └── cfr-0.152.jar     # CFR反编译工具
├── work/                      # 工作目录
│   ├── prod/                 # 生产环境数据
│   ├── test_local/           # 本地测试数据
│   └── output/               # 输出报告
└── README_v2.md              # 本文档
```

## 数据关联关系

### 数据库关联图
```
services (服务)
    ├── jar_files (JAR文件)
    │   └── java_source_in_jar_files (多对多关联)
    │       └── java_source_files (源码)
    └── class_files (Class文件)
        └── java_source_file_id (直接关联)
            └── java_source_files (源码)
```

### 关键特性
- **一对一关系**: Class文件与Java源码文件是一对一关系
- **多对多关系**: JAR文件与Java源码文件是多对多关系
- **外键约束**: 确保数据完整性和一致性
- **级联删除**: 自动清理关联数据

## 性能优化

### 数据库优化
- 合理的索引设计
- 分页查询支持
- 批量操作优化
- 连接池管理

### 处理优化
- 并行处理支持
- 增量更新机制
- 资源管理

## 监控和维护

### 日志管理
- 结构化日志记录
- 错误追踪和报告
- 性能监控

### 数据维护
- 定期数据清理
- 备份和恢复
- 数据迁移支持

### 健康检查
- 数据库连接检查
- 服务状态监控
- 处理进度跟踪

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库URL配置
   - 确认数据库服务状态
   - 验证用户权限

2. **反编译失败**
   - 确认CFR工具路径
   - 检查Java环境
   - 验证文件权限

3. **文件路径错误**
   - 检查配置文件路径
   - 确认目录存在
   - 验证路径权限

### 调试模式
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 干运行模式
python cleanup_orphaned_sources.py --all-services --dry-run
```

## 版本历史

### V2.0 (当前版本)
- 基于数据库的架构重构
- 按服务处理支持
- 完整的自动化流程
- 孤立源码清理功能
- 多环境支持

### V1.0 (原始版本)
- 基于CSV文件的处理
- 基本的JAR分析功能
- 简单的反编译支持

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证。详情请参阅LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮件联系
- 内部文档
