# Source Code Difference Analysis System Design Document

## 1. Overview

### 1.1 Purpose
This document outlines the design for a web-based system that analyzes and compares source code differences between services and their latest versions. The system will help development teams identify version inconsistencies and understand code changes across different service deployments.

### 1.2 Scope
- Import and store JAR/Class file analysis data from CSV reports
- Import and store decompiled source code from local directories
- Calculate and store differences between service versions
- Provide web interface for browsing and comparing source code differences
- Support search functionality across services and source files

### 1.3 Key Requirements
- **Data Import**: Import analysis reports and decompiled source code
- **Difference Calculation**: Compare service files against latest versions
- **Web Interface**: Provide user-friendly interface for browsing differences
- **Search Capability**: Enable searching across services and source code
- **Performance**: Handle large volumes of source code efficiently

## 2. System Architecture

### 2.1 High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Import   │    │   Web Service   │    │   Frontend UI   │
│                 │    │                 │    │                 │
│ - CSV Parser    │───▶│ - REST API      │◀───│ - React/Vue     │
│ - Source Reader │    │ - Diff Engine   │    │ - Code Viewer   │
│ - Diff Calc     │    │ - Search Engine │    │ - Diff Display  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Database Layer                           │
│                                                                 │
│ - Services & Files Metadata                                    │
│ - Source Code Storage                                          │
│ - Difference Results                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### 2.2.1 Data Import Layer
- **CSV Parser**: Parse analysis reports and extract service/file information
- **Source Reader**: Read decompiled source code from file system
- **Difference Calculator**: Compare files and calculate differences

#### 2.2.2 Web Service Layer
- **REST API**: Provide HTTP endpoints for data access
- **Difference Engine**: Calculate and serve difference information
- **Search Engine**: Enable searching across services and source code

#### 2.2.3 Frontend Layer
- **Service Browser**: List and browse services
- **Difference Viewer**: Display code differences with syntax highlighting
- **Search Interface**: Provide search functionality

## 3. Data Model

### 3.1 Core Entities

#### 3.1.1 Service
- **Purpose**: Represent a service deployment
- **Key Attributes**: name, IP address, port, username, password, server_base_path, jar_path, classes_path, source_path, description
- **Relationships**: has many JAR files, has many Java source files, has many differences

#### 3.1.2 JAR File
- **Purpose**: Represent a JAR file belonging to a specific service
- **Key Attributes**: name, size, last_modified, is_third_party, is_latest, decompile_path
- **Relationships**: belongs to service, has many Java source files

#### 3.1.3 Java Source File
- **Purpose**: Represent decompiled Java source code
- **Key Attributes**: class_full_name, file_path, content, size, last_modified, is_latest, hash, line_count
- **Relationships**: belongs to service, optionally belongs to JAR file

#### 3.1.4 Difference
- **Purpose**: Represent code differences between versions
- **Key Attributes**: type (added/deleted/modified), line_number, old_content, new_content, context
- **Relationships**: belongs to service and Java source file

### 3.2 Data Flow
```
CSV Reports → Service/JAR File Metadata → Database
     ↓
Decompiled Sources → Java Source Files → Database
     ↓
Difference Calculation → Difference Results → Database
     ↓
Web API → Frontend Display
```

### 3.3 Java Class Full Name Derivation Rules

#### 3.3.1 From JAR Decompiled Sources
- **Directory Structure**: `{jar_name}/{timestamp}-{service}@{ip}/com/package/ClassName.java`
- **Class Full Name**: `com.package.ClassName`
- **Inner Classes**: `com.package.OuterClass$InnerClass`
- **Anonymous Classes**: `com.package.OuterClass$1`

#### 3.3.2 From Class Decompiled Sources  
- **Directory Structure**: `{class_name}/{timestamp}-{service}@{ip}/com/package/ClassName.java`
- **Class Full Name**: `com.package.ClassName`
- **Inner Classes**: `com.package.OuterClass$InnerClass`

#### 3.3.3 File Traversal Rules
- **Exclude Directories**: Skip `_jar` and `_class` directories
- **Java Files Only**: Process only `.java` files
- **Path Parsing**: Extract class full name from file path relative to timestamp directory
- **Service Identification**: Extract service name from timestamp directory format `{timestamp}-{service}@{ip}`
- **JAR Association**: For JAR sources, associate with JAR file based on parent directory name

### 3.4 Data Import Rules

#### 3.4.1 Service Information Import
- **Source**: `work/prod/server_info.csv`
- **Mapping**: Import all columns (ip, port, username, password, service_name, server_base_path, jar_path, classes_path, source_path)
- **Validation**: Ensure service_name is unique

#### 3.4.2 JAR File Information Import
- **Source**: `work/output/jar_analysis_report_20251007.csv`
- **Mapping**: Extract JAR file metadata (name, size, last_modified, is_third_party, is_latest)
- **Service Association**: Link JAR files to services based on service columns in CSV

#### 3.4.3 Java Source File Import
- **JAR Sources**: Traverse `work/prod/lib-decompile/` directory
- **Class Sources**: Traverse `work/prod/classes-decompile/` directory
- **Exclusion**: Skip `_jar` and `_class` directories
- **Processing**: For each `.java` file:
  - Extract class full name from file path
  - Identify service from timestamp directory
  - Associate with JAR file (if from JAR source)
  - Calculate file properties (size, hash, line count)
  - **Note**: `is_latest` flag will be determined in a separate stage after all files are imported

#### 3.4.4 Latest Version Determination Stage
- **Prerequisite**: All Java source files must be imported first
- **Process**: 
  1. Group all Java source files by `class_full_name`
  2. For each class, find the file with the most recent `last_modified` timestamp
  3. Set `is_latest = true` for the latest version, `is_latest = false` for others
  4. Update database records with the `is_latest` flag

#### 3.4.5 Difference Calculation Stage
- **Prerequisite**: Latest version determination must be completed
- **Comparison Rule**: Always compare current Java source file against the latest version of the same class across all services
- **Time-based Ordering**: Use modification time to determine old vs new files
- **Algorithm**: Use line-by-line diff algorithm with time-based comparison
- **Storage**: Store differences with context and line numbers
- **Types**: Track added, deleted, and modified lines
- **Latest Version**: The file with the most recent modification time across all services is considered the latest version

### 3.5 Data Import Workflow

#### 3.5.1 Stage 1: Initial Data Import
1. **Import Services**: Load service information from `server_info.csv`
2. **Import JAR Files**: Load JAR file metadata from analysis reports
3. **Import Java Source Files**: Traverse decompiled directories and import all `.java` files
4. **Set Initial Flags**: Set `is_latest = false` for all Java source files initially

#### 3.5.2 Stage 2: Latest Version Determination
1. **Group by Class**: Group all Java source files by `class_full_name`
2. **Find Latest**: For each class group, identify the file with the most recent `last_modified` timestamp
3. **Update Flags**: Set `is_latest = true` for the latest version, `is_latest = false` for others
4. **Database Update**: Batch update the `is_latest` flag in the database

#### 3.5.3 Stage 3: Difference Calculation
1. **Query Latest Versions**: For each service, find Java source files where `is_latest = false`
2. **Find Corresponding Latest**: For each outdated file, find the corresponding latest version
3. **Calculate Differences**: Compare outdated version against latest version
4. **Store Results**: Save difference results to the database

### 3.6 Difference Comparison Rules

#### 3.6.1 Core Comparison Logic
- **Target**: Always compare current Java source file against the latest version of the same class across all services
- **Time-based Determination**: Use `last_modified` timestamp to identify old vs new files
- **Latest Version**: The Java source file with the most recent `last_modified` time across all services is considered the latest version
- **Comparison Direction**: Old file (earlier timestamp) → New file (later timestamp)

#### 3.6.2 Difference Types
- **Added Lines**: Lines present in new file but not in old file
- **Deleted Lines**: Lines present in old file but not in new file  
- **Modified Lines**: Lines that exist in both files but with different content
- **Context**: Include surrounding lines for better understanding

#### 3.6.3 Comparison Algorithm
1. **Find Latest Version**: Query all services for the same `class_full_name` where `is_latest = true`
2. **Find Current Version**: Query the specific service's version of the same `class_full_name`
3. **Compare Versions**: Compare current version against the latest version
4. **Store Differences**: Save differences with line numbers and context
5. **Note**: Latest version marking is done in a separate stage before difference calculation

#### 3.6.4 Example Scenario
```
Service A: com.example.MyClass (2025-01-01 10:00:00) - OLD
Service B: com.example.MyClass (2025-01-02 15:30:00) - LATEST
Service C: com.example.MyClass (2025-01-01 14:20:00) - OLD

Comparison:
- Service A vs Service B: Show differences (A is old, B is new)
- Service C vs Service B: Show differences (C is old, B is new)
- Service B: Marked as latest version
```

## 4. Database Design

### 4.1 Core Tables

#### 4.1.1 Services Table
```sql
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
```

#### 4.1.2 JAR Files Table
```sql
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
```

#### 4.1.3 Java Source Files Table
```sql
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
```

#### 4.1.4 Differences Table
```sql
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
```

### 4.2 Indexing Strategy
```sql
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
```

## 5. API Design

### 5.1 Service Management APIs
- **GET /api/services**: List all services with pagination
- **GET /api/services/{id}**: Get service details including configuration
- **GET /api/services/{id}/jar-files**: Get service JAR files
- **GET /api/services/{id}/java-classes**: Get service Java source files

### 5.2 Difference Analysis APIs
- **GET /api/services/{id}/differences**: Get service differences overview
- **GET /api/services/{id}/java-classes/{classId}/differences**: Get Java class differences (compared against latest version across all services)
- **GET /api/services/{id}/java-classes/{classId}/source**: Get Java source code content
- **GET /api/services/{id}/jar-files/{jarId}/java-classes**: Get JAR file's Java classes
- **GET /api/java-classes/{classFullName}/latest**: Get the latest version of a Java class across all services

### 5.3 Search APIs
- **GET /api/search/services**: Search services by name
- **GET /api/search/java-classes**: Search Java classes by full name
- **GET /api/search/source**: Search source code content
- **GET /api/search/jar-files**: Search JAR files by name

## 6. Technology Stack

### 6.1 Backend
- **Database**: MySQL 8.0+
- **Web Framework**: FastAPI (Python) or Spring Boot (Java)
- **Task Queue**: Celery (Python) or Redis Queue
- **Cache**: Redis for performance optimization

### 6.2 Frontend
- **Framework**: Vue 3+
- **UI Components**: Element Plus
- **Code Editor**: CodeMirror
- **Diff Display**: Vue-diff

### 6.3 Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus + Grafana

## 7. Implementation Phases

### 7.1 Phase 1: Data Import (2-3 weeks)
- **Database Setup**: Create tables and indexes
- **CSV Import**: Develop CSV parsing and import tools for services and JAR files
- **Source Import**: Develop Java source code import functionality with class name derivation
- **File Traversal**: Implement directory traversal rules for decompiled sources
- **Latest Version Determination**: Implement algorithm to determine latest versions across all services
- **Difference Calculation**: Implement diff algorithms for Java source files

### 7.2 Phase 2: Web API (2-3 weeks)
- **API Framework**: Set up web framework and basic structure
- **Core APIs**: Implement service, JAR file, and Java class management APIs
- **Difference APIs**: Implement Java source code difference analysis endpoints
- **Search APIs**: Implement search functionality for services, JAR files, and Java classes

### 7.3 Phase 3: Frontend (2-3 weeks)
- **Project Setup**: Initialize Vue 3+ project with Element Plus
- **Service Browser**: Implement service listing and browsing
- **Java Class Viewer**: Implement Java source code viewing with CodeMirror
- **Difference Viewer**: Implement code difference display with Vue-diff
- **Search Interface**: Implement search functionality for services and Java classes

### 7.4 Phase 4: Integration & Deployment (1-2 weeks)
- **System Integration**: Integrate all components
- **Performance Optimization**: Optimize queries and caching
- **Deployment**: Set up production environment
- **Testing**: Comprehensive testing and bug fixes

## 8. Key Considerations

### 8.1 Performance
- **Large Data Handling**: Efficient storage and retrieval of large source files
- **Indexing**: Proper database indexing for fast queries
- **Caching**: Strategic caching of frequently accessed data
- **Pagination**: Implement pagination for large result sets

### 8.2 Scalability
- **Horizontal Scaling**: Design for multiple service instances
- **Database Scaling**: Consider read replicas and partitioning
- **File Storage**: Consider distributed file storage for large files
- **Load Balancing**: Implement load balancing for web services

### 8.3 Security
- **Access Control**: Implement authentication and authorization
- **Data Protection**: Protect sensitive source code
- **API Security**: Secure API endpoints and data transmission
- **Audit Logging**: Track system access and changes

### 8.4 Maintainability
- **Code Organization**: Clean, modular code structure
- **Documentation**: Comprehensive code and API documentation
- **Testing**: Unit, integration, and end-to-end tests
- **Monitoring**: System health monitoring and alerting

## 9. Success Criteria

### 9.1 Functional Requirements
- ✅ Successfully import analysis reports and source code
- ✅ Calculate and store accurate differences
- ✅ Provide intuitive web interface for browsing differences
- ✅ Support efficient search across services and code

### 9.2 Performance Requirements
- ✅ Handle 1000+ services and 10000+ files
- ✅ Response time < 2 seconds for common operations
- ✅ Support concurrent users (10+ simultaneous)
- ✅ Efficient storage utilization

### 9.3 Usability Requirements
- ✅ Intuitive user interface
- ✅ Clear difference visualization
- ✅ Fast search and navigation
- ✅ Responsive design for different screen sizes

## 10. Next Steps

1. **Review and Approval**: Review this design document with stakeholders
2. **Technology Selection**: Finalize technology stack choices
3. **Detailed Planning**: Create detailed implementation plans for each phase
4. **Environment Setup**: Set up development and testing environments
5. **Team Assignment**: Assign team members to different components
6. **Development Start**: Begin Phase 1 implementation

## 11. API Response Examples

### 11.1 Service Differences Overview
```json
{
    "service_id": 1,
    "service_name": "dsop_cmpp",
    "total_java_classes": 45,
    "outdated_classes": 12,
    "differences_summary": {
        "jar_files": {
            "total": 37,
            "outdated": 8,
            "modified": 5,
            "added": 2,
            "deleted": 1
        },
        "java_classes": {
            "total": 8,
            "outdated": 4,
            "modified": 3,
            "added": 1,
            "deleted": 0
        }
    },
    "last_updated": "2025-01-07T10:30:00Z"
}
```

### 11.2 Java Class Differences Detail
```json
{
    "java_source_file_id": 123,
    "class_full_name": "com.justinmobile.cmpp.Config",
    "service_name": "dsop_cmpp",
    "current_version": {
        "last_modified": "2025-01-01T10:00:00Z",
        "is_latest": false
    },
    "latest_version": {
        "service_name": "dsop_core",
        "last_modified": "2025-01-02T15:30:00Z",
        "is_latest": true
    },
    "differences": [
        {
            "difference_type": "modified",
            "line_number": 45,
            "old_content": "private String oldConfig = \"default\";",
            "new_content": "private String newConfig = \"updated\";",
            "context": "Configuration class initialization"
        },
        {
            "difference_type": "added",
            "line_number": 67,
            "old_content": null,
            "new_content": "private String newField = \"value\";",
            "context": "New field addition"
        }
    ],
    "total_differences": 15,
    "comparison_note": "Compared against latest version from dsop_core service"
}
```

---

*This document serves as the foundation for the Source Code Difference Analysis System. It will be updated as the project evolves and requirements become more detailed.*
