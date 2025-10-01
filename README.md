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

### 1. jar_analyzer.py - JAR Package Analyzer

Analyze JAR package version information for each service in test environment and generate detailed CSV reports.

**Features:**
- Parse JAR file information (size, modification date, etc.)
- Identify third-party dependencies
- Compare JAR package versions across different services
- Generate column names including IP addresses and service names
- Support progress display

**Usage:**
```bash
# Analyze from local files (basic usage)
python jar_analyzer.py --data-dir work/uat/jar-info --output-file work/output/jar_analysis_report.csv

# Get JAR information directly from servers
python jar_analyzer.py --server-list-file work/uat/lib_info.csv --output-file work/output/jar_analysis_report.csv

# Use custom internal dependency prefix file
python jar_analyzer.py --server-list-file work/uat/lib_info.csv --internal-prefix-file my_prefixes.txt --output-file work/output/jar_analysis_report.csv
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
- Column definition: `ip_address,port,username,password,service_name,jar_file_directory`
- Example content:
```csv
ip_address,port,username,password,service_name,jar_file_directory
10.176.24.135,22,root,password,ui,/opt/apps/ui/lib
10.176.24.156,22,root,password,query,/opt/apps/query/lib
local_service,22,,,local_service,/path/to/local/jar/directory
```
- **Local Directory Support**: If `username` and `password` are empty, the tool will treat `jar_file_directory` as a local directory path
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

### 2. jar_decompiler.py - JAR File Decompiler Tool

Fetch specified JAR files from multiple servers, decompile them for subsequent comparison analysis.

**Features:**
- Locate JAR file positions from JAR analysis results
- Support multi-threaded parallel downloads
- Use CFR tool for decompilation
- Organize output directories by timestamp and service information
- Comprehensive error handling and progress display

**Usage:**
```bash
# Basic usage (output directory defaults to work/{jar_name_without_ext})
python jar_decompiler.py my_app_commons-session-2.1.0.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv

# Specify custom output directory
python jar_decompiler.py my_app_commons-session-2.1.0.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv --output-dir work/custom_output
```

**Input Parameter Formats:**

**1. JAR Analysis Result File (--analysis-csv)**
- File format: CSV file generated by jar_analyzer.py
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1
- Required columns: JAR filename, JAR information columns for each service

**2. Server Connection Information File (--server-list-file)**
- File format: CSV file
- Column definition: `ip_address,port,username,password,service_name,jar_file_directory`
- Example content:
```csv
ip_address,port,username,password,service_name,jar_file_directory
10.0.0.135,22,root,password,ui,/opt/apps/ui/lib
10.0.0.156,22,root,password,query,/opt/apps/query/lib
local_service,22,,,local_service,/path/to/local/jar/directory
```
- **Local Directory Support**: If `username` and `password` are empty, the tool will treat `jar_file_directory` as a local directory path
- Encoding support: UTF-8-SIG, UTF-8, GBK, GB2312, Latin-1

**Output Directory Naming Rules:**
- Default directory name: `work/{jar_name_without_ext}` (automatically remove .jar extension)
- Example: `my_app_commons-session-2.1.0.jar` → `work/my_app_commons-session-2.1.0`
- Custom directory: Specify via `--output-dir` parameter

**Output Directory Structure:**
```
work/my_app_commons-session-2.1.0/                    # Main output directory
├── _jar/                                          # JAR file storage directory
│   ├── ui@10.0.0.135/                    # Organized by service_name@IP_address
│   │   └── my_app_commons-session-2.1.0.jar         # Original JAR file
│   ├── query@10.176.24.156/
│   │   └── my_app_commons-session-2.1.0.jar
│   └── ...
└── 20230321-ui@10.0.0.135/               # Decompilation result directory
    ├── com/                                       # Decompiled Java source code
    │   └── (Java class files)
    └── summary.txt                                # Decompilation summary
```

**Directory Naming Rules Details:**

**1. JAR File Storage Directory (_jar/)**
- Format: `{service_name}@{IP_address}/`
- Example: `ui@10.0.0.135/`
- Purpose: Store original JAR files downloaded from servers

**2. Decompilation Result Directory**
- Format: `{YYYYMMDD}-{service_name}@{IP_address}/`
- Timestamp source: JAR file's last modification date
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

**2. Run JAR Analyzer**
```bash
python jar_analyzer.py --data-dir work/uat/jar-info --output-file work/output/jar_analysis_report.csv
```

**3. Prepare Server Connection Information**
Create `work/uat/lib_info.csv` file containing server connection information.

**4. Run Decompiler Tool**
```bash
python jar_decompiler.py myapp.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv
```

### Method 2: Get Directly from Servers (Recommended)

**1. Prepare Server Connection Information**
Create `work/uat/lib_info.csv` file containing server connection information.

**2. Run JAR Analyzer (Get from Servers)**
```bash
python jar_analyzer.py --server-list-file work/uat/lib_info.csv --output-file work/output/jar_analysis_report.csv
```

**3. Run Decompiler Tool**
```bash
python jar_decompiler.py myapp.jar --analysis-csv work/output/jar_analysis_report.csv --server-list-file work/uat/lib_info.csv
```

### 4. Comparison Analysis

Use comparison tools (such as Beyond Compare, WinMerge, etc.) to compare decompilation result directories.

## Configuration

### Third-Party Dependency Recognition

**Custom Internal Dependency Prefixes:**
You can specify a custom prefix file via the `--internal-prefix-file` parameter:
```bash
python jar_analyzer.py --server-list-file work/uat/lib_info.csv --internal-prefix-file my_prefixes.txt --output-file work/output/jar_analysis_report.csv
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
├── jar_analyzer.py          # JAR package analyzer
├── jar_decompiler.py        # JAR file decompiler tool
├── decompiler.py            # Original decompiler tool
├── requirements.txt         # Python dependencies
├── README.md               # Project documentation
├── assets/
│   └── jar/
│       └── cfr-0.152.jar   # CFR decompilation tool
├── work/                   # Working directory
│   ├── uat/
│   │   └── jar-info/       # JAR information files
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
6. **Parameter Mutual Exclusivity**: jar_analyzer.py's `--data-dir` and `--server-list-file` parameters cannot be used together
7. **Local Directory Support**: When username/password are empty in server list file, tools will read from local directories instead of remote servers

## Troubleshooting

### Common Issues

1. **Connection Timeout**: Check network connection and server status
2. **Permission Denied**: Confirm SSH username and password are correct
3. **File Not Found**: Check if JAR file path is correct
4. **Decompilation Failed**: Confirm Java environment is configured correctly
5. **Encoding Error**: Tool automatically detects encoding, if problems persist please check file format
6. **Parameter Conflict**: Ensure jar_analyzer.py uses only one of `--data-dir` or `--server-list-file`

### Log Information

The tool outputs detailed progress information and error messages to facilitate problem diagnosis.

## Contributing

Welcome to submit Issues and Pull Requests to improve this tool.

## License

This project is licensed under the MIT License.