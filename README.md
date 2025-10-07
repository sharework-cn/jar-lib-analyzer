# Java Library Analyzer

A toolset for analyzing Java JAR package version information and decompiling them, helping development teams manage and compare JAR package versions across different services.

## Background

In our platform deployment process, updates are not performed as full deployments. Some services may not have their JAR packages updated in a timely manner during the update process. This creates a need to:

1. **Identify outdated JAR packages**: Determine which services contain JAR packages that are not the latest version
2. **Compare differences**: Analyze the specific differences between JAR packages across different services
3. **Ensure consistency**: Maintain version consistency across all services in the platform

This tool addresses these needs by providing comprehensive analysis and comparison capabilities for JAR package versions across multiple services and servers.

## Features

- **JAR Package Version Analysis**: Analyze JAR package version information for each service in test environment
- **Third-Party Dependency Recognition**: Automatically identify internal and third-party dependencies
- **Multi-Server Support**: Support fetching JAR files from multiple servers
- **Decompilation Functionality**: Use CFR tool to decompile JAR files
- **Structured Output**: Generate CSV reports and organized directory structures
- **Encoding Compatibility**: Support multiple encoding formats (UTF-8, GBK, ANSI, etc.)

## Tool Components

### 1. analyzer.py - JAR/Class Package Analyzer

Analyze JAR and class file version information for each service in test environment and generate detailed CSV reports.

**Features:**
- Parse JAR and class file information (size, modification date, etc.)
- Extract class full names from .class file paths
- Identify third-party dependencies
- Compare file versions across different services
- Generate column names including IP addresses and service names
- Support progress display

**Usage:**
```bash
# Analyze JAR files from local files (basic usage)
python analyzer.py --data-dir work/uat/jar-info --output-file work/output/jar_analysis_report.csv

# Analyze class files from local files
python analyzer.py --data-dir work/uat/classes-info --output-file work/output/classes_analysis_report.csv --classes-dir classes

# Get file information directly from servers
python analyzer.py --server-list-file work/uat/lib_info.csv --output-file work/output/jar_analysis_report.csv

# Use custom internal dependency prefix file
python analyzer.py --server-list-file work/uat/lib_info.csv --internal-prefix-file my_prefixes.txt --output-file work/output/jar_analysis_report.csv
```

**Input Parameter Formats:**

**1. JAR Information Files (--data-dir mode)**
- File location: Under `work/uat/jar-info/` directory
- File naming: `IP_address_service_name.txt` (e.g., `10.176.24.135_ui.txt`)
- File content format:
```
-rw-r--r-- 1 root root 1234567 2024-01-01 12:30:45 myapp.jar
-rw-r--r-- 1 root root 2345678 2024-01-01 12:31:00 another.jar
```
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1

**2. Server Connection Information File (--server-list-file mode)**
- File format: CSV file
- **Format 1 (6 columns)**: `ip_address,port,username,password,service_name,jar_file_directory`
- **Format 2 (7 columns)**: `ip_address,port,username,password,service_name,jar_file_directory,class_file_directory`
- **Format 3 (9 columns)**: `ip_address,port,username,password,service_name,server_base_path,jar_file_directory,class_file_directory,source_path`
- Example content (6 columns):
```csv
ip_address,port,username,password,service_name,jar_file_directory
10.176.24.135,22,root,password,ui,/opt/apps/ui/lib
10.176.24.156,22,root,password,query,/opt/apps/query/lib
local_service,22,,,local_service,/path/to/local/jar/directory
```
- Example content (7 columns):
```csv
ip_address,port,username,password,service_name,jar_file_directory,class_file_directory
10.176.24.135,22,root,password,ui,/opt/apps/ui/lib,/opt/apps/ui/classes
10.176.24.156,22,root,password,query,/opt/apps/query/lib,/opt/apps/query/classes
local_service,22,,,local_service,/path/to/local/jar/directory,/path/to/local/classes/directory
```
- Example content (9 columns with variable support):
```csv
ip_address,port,username,password,service_name,server_base_path,jar_file_directory,class_file_directory,source_path
10.176.24.135,22,root,password,ui,/app/apprun/tomcat_server/webapps/ui/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,tsm_2.0/tsm_ui
10.176.24.156,22,root,password,query,/app/apprun/tomcat_server/webapps/query/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,tsm_2.0/tsm_query
local_service,22,,,local_service,/app/apprun/tomcat_server/webapps/local/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,local_source
```
- **Local Directory Support**: If `username` and `password` are empty, the tool will treat directories as local paths
- **Class File Support**: When using 7-column or 9-column format, `class_file_directory` is used for class file locations
- **Variable Replacement**: In 9-column format, `{service_name}` and `{server_base_path}` variables in paths are automatically replaced with actual values
- **Backward Compatibility**: 6-column and 7-column formats are supported for backward compatibility
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1

**3. Internal Dependency Prefix File (--internal-prefix-file)**
- File format: Text file, one prefix per line
- Example content:
```
my_custom_prefix
```
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1
- Default prefixes: If no file is specified, use built-in 15 default prefixes

**Output Format:**
- CSV file containing JAR filename and third-party dependency identification
- Each service occupies three columns: size, last update date, is latest
- Column name format: `service_name_IP_address_attribute` (dots in IP address replaced with underscores)
- Output encoding: UTF-8-SIG (UTF-8 with BOM)

### 2. decompiler.py - JAR/Class File Decompiler Tool

Fetch specified JAR or class files from multiple servers, decompile them for subsequent comparison analysis.

**Features:**
- Support both JAR and class file decompilation
- Support single file decompilation and service-based batch decompilation
- Locate file positions from analysis results
- Support multi-threaded parallel downloads
- Use CFR tool for decompilation
- Organize output directories by timestamp and service information
- Comprehensive error handling and progress display

**Usage:**
```bash
# JAR file decompilation (output directory defaults to work/{jar_name_without_ext})
python decompiler.py my_app_commons-session-2.1.0.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type jar

# Class file decompilation
python decompiler.py com.example.MyClass --analysis-csv work/output/classes_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type class

# Service-based decompilation (decompile all non-third-party files for a service)
python decompiler.py service_name --analysis-csv work/output/classes_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type class

# Specify custom output directory
python decompiler.py my_app_commons-session-2.1.0.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type jar --output-dir work/custom_output
```

**Input Parameter Formats:**

**1. Analysis Result File (--analysis-csv)**
- File format: CSV file generated by analyzer.py
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1
- Required columns: JAR filename, JAR information columns for each service

**2. Server Connection Information File (--server-list-file)**
- File format: CSV file
- **Format 1 (6 columns)**: `ip_address,port,username,password,service_name,jar_file_directory`
- **Format 2 (7 columns)**: `ip_address,port,username,password,service_name,jar_file_directory,class_file_directory`
- **Format 3 (9 columns)**: `ip_address,port,username,password,service_name,server_base_path,jar_file_directory,class_file_directory,source_path`
- Example content (6 columns):
```csv
ip_address,port,username,password,service_name,jar_file_directory
10.0.0.135,22,root,password,ui,/opt/apps/ui/WEB-INF/lib
10.0.0.156,22,root,password,query,/opt/apps/query/WEB-INF/lib
local_service,22,,,local_service,/path/to/local/jar/directory
```
- Example content (7 columns):
```csv
ip_address,port,username,password,service_name,jar_file_directory,class_file_directory
10.0.0.135,22,root,password,ui,/opt/apps/ui/WEB-INF/lib,/opt/apps/ui/WEB-INF/classes
10.0.0.156,22,root,password,query,/opt/apps/query/WEB-INF/lib,/opt/apps/query/WEB-INF/classes
local_service,22,,,local_service,/path/to/local/jar/directory,/path/to/local/classes/directory
```
- Example content (9 columns with variable support):
```csv
ip_address,port,username,password,service_name,server_base_path,jar_file_directory,class_file_directory,source_path
10.0.0.135,22,root,password,ui,/app/apprun/tomcat_server/webapps/ui/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,tsm_2.0/tsm_ui
10.0.0.156,22,root,password,query,/app/apprun/tomcat_server/webapps/query/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,tsm_2.0/tsm_query
local_service,22,,,local_service,/app/apprun/tomcat_server/webapps/local/WEB-INF,work/prod/lib-download/{service_name}{server_base_path}/lib,work/prod/classes-download/{service_name}{server_base_path}/classes,local_source
```
- **Local Directory Support**: If `username` and `password` are empty, the tool will treat directories as local paths
- **JAR Files**: Use `jar_file_directory` for JAR file locations
- **Class Files**: Use `class_file_directory` for class file locations (base directory without package directories)
- **Variable Replacement**: In 9-column format, `{service_name}` and `{server_base_path}` variables in paths are automatically replaced with actual values
- **Backward Compatibility**: 6-column and 7-column formats are supported for backward compatibility
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1

**Service-Based Decompilation:**
When the `file_name` parameter is a service name (without file extensions), the tool will:
- Automatically identify all non-third-party files belonging to that service
- Download and decompile all identified files in batch
- Maintain the same directory structure as single file decompilation
- Only process files marked as internal dependencies (Third_Party_Dependency = 'No')

**Output Directory Naming Rules:**
- Default directory name: `work/{file_name_without_ext}` (automatically remove .jar/.class extension)
- Example: `my_app_commons-session-2.1.0.jar` → `work/my_app_commons-session-2.1.0`
- Example: `com.example.MyClass` → `work/com.example.MyClass`
- Custom directory: Specify via `--output-dir` parameter

**Output Directory Structure:**

**JAR File Decompilation:**
```
work/my_app_commons-session-2.1.0/                    # Main output directory
├── _jar/                                          # JAR file storage directory
│   ├── ui@10.0.0.135/                    # Organized by service_name@IP_address
│   │   └── my_app_commons-session-2.1.0.jar         # Original JAR file
│   ├── query@10.176.24.156/
│   │   └── my_app_commons-session-2.1.0.jar
│   └── ...
└── my_app_commons-session-2.1.0/                   # JAR name subdirectory
    └── 20230321-ui@10.0.0.135/               # Decompilation result directory
        ├── com/                                       # Decompiled Java source code
        │   └── (Java class files)
        └── summary.txt                                # Decompilation summary
```

**Class File Decompilation:**
```
work/com.example.MyClass/                            # Main output directory
├── _class/                                         # Class file storage directory
│   ├── ui@10.0.0.135/                    # Organized by service_name@IP_address
│   │   └── com.example.MyClass.class               # Original class file
│   └── ...
└── com.example.MyClass/                            # Class name subdirectory
    └── 20230321-ui@10.0.0.135/               # Decompilation result directory
        └── MyClass.java                               # Decompiled Java source code
```

**Directory Naming Rules Details:**

**1. File Storage Directory (_jar/ or _class/)**
- Format: `{service_name}@{IP_address}/`
- Example: `ui@10.0.0.135/`
- Purpose: Store original files downloaded from servers

**2. Decompilation Result Directory**
- Format: `{YYYYMMDD}-{service_name}@{IP_address}/`
- Timestamp source: File's last modification date
- Example: `20230321-ui@10.0.0.135/`
- Purpose: Store Java source code generated by CFR decompilation tool
- Time format: YYYY-MM-DD

## Installation

```bash
pip install -r requirements.txt
```

**Dependencies:**
- pandas>=1.3.0
- openpyxl>=3.0.0
- paramiko>=2.7.0
- scp>=0.14.0

## Requirements

- Python 3.6+
- Java 8+ (for running CFR decompilation tool)
- CFR-0.152.jar (included in assets/jar/ directory)

## Usage Workflow

### Method 1: Analyze from Local Files

**1. Prepare JAR Information Files**
- Save JAR file information from each server as txt files
- File location: `work/uat/jar-info/` directory
- File naming: `IP_address_service_name.txt` (e.g., `10.0.0.135_ui.txt`)
- File content format:
```
-rw-r--r-- 1 root root 1234567 2024-01-01 12:30:45 myapp.jar
-rw-r--r-- 1 root root 2345678 2024-01-01 12:31:00 another.jar
```

**2. Run Analyzer**
```bash
python analyzer.py --data-dir work/uat/jar-info --output-file work/output/jar_analysis_report.csv
```

**3. Prepare Server Connection Information**
Create `work/uat/lib_info.csv` file containing server connection information.

**4. Run Decompiler Tool**
```bash
python decompiler.py myapp.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type jar
```

### Method 2: Get Directly from Servers (Recommended)

**1. Prepare Server Connection Information**
Create `work/uat/lib_info.csv` file containing server connection information.

**2. Run Analyzer (Get from Servers)**
```bash
python analyzer.py --server-list-file work/uat/lib_info.csv --output-file work/output/jar_analysis_report.csv
```

**3. Run Decompiler Tool**
```bash
python decompiler.py myapp.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv --file-type jar
```

### 4. Comparison Analysis

Use comparison tools (such as Beyond Compare, WinMerge, etc.) to compare decompilation result directories.

## Configuration

### Third-Party Dependency Recognition

**Custom Internal Dependency Prefixes:**
You can specify a custom prefix file via the `--internal-prefix-file` parameter:
```bash
python analyzer.py --server-list-file work/uat/lib_info.csv --internal-prefix-file my_prefixes.txt --output-file work/output/jar_analysis_report.csv
```

Prefix file format (one prefix per line):
```
my_custom_prefix1
my_custom_prefix2
```

Other JAR files will be marked as third-party dependencies.

### Latest Version Determination

The tool determines whether a JAR file is the latest version by comparing file sizes. If the file sizes are the same, it is considered the latest version.

## Directory Structure

```
java-lib-analyzer/
├── analyzer.py              # JAR/Class package analyzer
├── decompiler.py            # JAR/Class file decompiler tool
├── requirements.txt         # Python dependencies
├── README.md               # Project documentation
├── assets/
│   └── jar/
│       └── cfr-0.152.jar   # CFR decompilation tool
├── work/                   # Working directory
│   ├── uat/
│   │   ├── jar-info/       # JAR information files
│   │   └── classes-info/   # Class information files
│   └── output/             # Output files
└── .gitignore              # Git ignore file
```

## Encoding Support

**Supported Encoding Formats:**
- UTF-8-SIG (UTF-8 with BOM)
- UTF-8
- GBK
- GB2312
- Latin-1

**Automatic Encoding Detection:**
The tool automatically tries the above encoding formats in priority order until it successfully reads the file.

**Output Encoding:**
- CSV report files: UTF-8-SIG (UTF-8 with BOM), ensuring proper display of Chinese characters in Excel and other tools

## Notes

1. **Network Connection**: Ensure SSH connection to target servers is possible (when username/password provided)
2. **Permission Requirements**: Need permissions to read JAR files (both remote and local)
3. **Disk Space**: Decompilation process requires sufficient disk space
4. **Java Environment**: Ensure Java 8 or higher is installed on the system
5. **Encoding Format**: Input files support multiple encodings, output files use UTF-8-SIG encoding
6. **Parameter Mutual Exclusivity**: analyzer.py's `--data-dir` and `--server-list-file` parameters cannot be used together
7. **Local Directory Support**: When username/password are empty in server list file, tools will read from local directories instead of remote servers

## Troubleshooting

### Common Issues

1. **Connection Timeout**: Check network connection and server status
2. **Permission Denied**: Confirm SSH username and password are correct
3. **File Not Found**: Check if JAR file path is correct
4. **Decompilation Failed**: Confirm Java environment is configured correctly
5. **Encoding Error**: Tool automatically detects encoding, if problems persist please check file format
6. **Parameter Conflict**: Ensure analyzer.py uses only one of `--data-dir` or `--server-list-file`

### Log Information

The tool outputs detailed progress information and error messages to facilitate problem diagnosis.

## Contributing

Welcome to submit Issues and Pull Requests to improve this tool.

## License

This project is licensed under the MIT License.