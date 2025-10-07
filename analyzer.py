#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JAR File Analyzer
Analyze JAR package version information for each service in test environment and generate CSV reports
"""

import os
import re
import pandas as pd
from datetime import datetime
from collections import defaultdict
import argparse
import paramiko
from scp import SCPClient


class JarInfoParser:
    """JAR/Class file information parser"""
    
    def __init__(self, classes_dir="classes"):
        self.jar_pattern = re.compile(r'-rw[a-z-]*\s+\d+\s+\w+\s+\w+\s+(\d+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+(.+\.(?:jar|class))$')
        self.classes_dir = classes_dir
    
    def parse_file(self, file_path):
        """Parse content of a single file"""
        jar_files = []
        
        # Try different encoding formats
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        match = self.jar_pattern.match(line)
                        if match:
                            size = int(match.group(1))
                            date_str = match.group(2)
                            filename = match.group(3)
                            
                            # Parse date time (try both formats: with and without seconds)
                            modify_date = None
                            try:
                                # Try format with seconds first
                                modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                try:
                                    # Try format without seconds
                                    modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                                except ValueError:
                                    modify_date = None
                            
                            # Extract class name for .class files
                            display_name = filename
                            if filename.endswith('.class'):
                                class_name = self.extract_class_name(filename)
                                if class_name:
                                    display_name = class_name
                            
                            jar_files.append({
                                'filename': filename,
                                'display_name': display_name,
                                'size': size,
                                'modify_date': modify_date,
                                'date_str': date_str
                            })
                break  # Successfully parsed, break loop
            except UnicodeDecodeError:
                continue
        else:
            print(f"Error: Unable to read file {file_path} with any encoding format")
            
        return jar_files
    
    def extract_class_name(self, filepath):
        """Extract class full name from .class file path"""
        # Find classes directory in the path
        classes_index = filepath.find(f'/{self.classes_dir}/')
        if classes_index == -1:
            # Try without leading slash
            classes_index = filepath.find(self.classes_dir + '/')
            if classes_index == -1:
                return None
        
        # Extract path after classes directory
        if filepath.find(f'/{self.classes_dir}/') >= 0:
            # Skip the classes directory part (with leading slash)
            class_path = filepath[classes_index + len(f'/{self.classes_dir}/'):]
        else:
            # Skip the classes directory part (without leading slash)
            class_path = filepath[classes_index + len(self.classes_dir + '/'):]
        
        # Remove .class extension
        if class_path.endswith('.class'):
            class_path = class_path[:-6]  # Remove '.class'
        
        # Replace / with . to get class full name
        class_name = class_path.replace('/', '.')
        
        return class_name if class_name else None
    
    def parse_ssh_output(self, output):
        """Parse SSH command output"""
        jar_files = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            match = self.jar_pattern.match(line)
            if match:
                size = int(match.group(1))
                date_str = match.group(2)
                filename = match.group(3)
                
                # Parse date time (try both formats: with and without seconds)
                modify_date = None
                try:
                    # Try format with seconds first
                    modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try format without seconds
                        modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        modify_date = None
                
                # Extract class name for .class files
                display_name = filename
                if filename.endswith('.class'):
                    class_name = self.extract_class_name(filename)
                    if class_name:
                        display_name = class_name
                
                jar_files.append({
                    'filename': filename,
                    'display_name': display_name,
                    'size': size,
                    'modify_date': modify_date,
                    'date_str': date_str
                })
        
        return jar_files


class JarAnalyzer:
    """JAR file analyzer"""
    
    def __init__(self, data_dir=None, server_list_file=None, internal_prefix_file=None, classes_dir="classes"):
        self.data_dir = data_dir
        self.server_list_file = server_list_file
        self.internal_prefix_file = internal_prefix_file
        self.classes_dir = classes_dir
        self.parser = JarInfoParser(classes_dir=classes_dir)
        self.services_data = {}
        self.all_jars = set()
        self.server_df = None
        
        # Load internal dependency prefixes
        self.internal_prefixes = self._load_internal_prefixes()
        
    def extract_service_name(self, filename):
        """Extract service name from filename (service_name_IP_address format)"""
        # Remove .txt extension
        name_without_ext = filename[:-4]
        
        # Find IP address pattern (x.x.x.x) in the filename
        # IP address format is usually at the beginning: x.x.x.x_service_name
        parts = name_without_ext.split('_')
        if len(parts) >= 2:
            # Check if first part looks like an IP address (contains dots)
            if '.' in parts[0]:
                # First part is IP address, remaining parts form service name
                ip_address = parts[0]
                service_name = '_'.join(parts[1:])
                # Replace dots in IP address with underscores, format: service_name_IP_address
                ip_with_underscore = ip_address.replace('.', '_')
                full_service_name = f"{service_name}_{ip_with_underscore}"
            else:
                # No IP address pattern found, use service name only
                full_service_name = name_without_ext
        else:
            # If no underscore, use filename directly
            full_service_name = name_without_ext
        
        return full_service_name
    
    def _load_internal_prefixes(self):
        """Load internal dependency prefix list"""
        if self.internal_prefix_file and os.path.exists(self.internal_prefix_file):
            print(f"Loading internal dependency prefix file: {self.internal_prefix_file}")
            # Try different encoding formats
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    with open(self.internal_prefix_file, 'r', encoding=encoding) as f:
                        prefixes = [line.strip() for line in f if line.strip()]
                    print(f"Successfully loaded {len(prefixes)} internal dependency prefixes using encoding {encoding}")
                    return prefixes
                except UnicodeDecodeError:
                    continue
            else:
                print(f"Warning: Unable to read internal dependency prefix file with any encoding format")
        
        # Default internal dependency prefixes
        default_prefixes = [
            'dsop',
            'jim',
            'tsm',
            'cmpp',
            'card_market',
            'cmft',
            'customer_service',
            'cloud_encryptor',
            'encryptor_',
            'sim_',
            'smart_auth',
            'sp_',
            'student_card',
            'tp-',
            'tsn_'
        ]
        print(f"Using default internal dependency prefixes, total {len(default_prefixes)} prefixes")
        return default_prefixes
    
    def load_server_data(self):
        """Load server connection information"""
        if not self.server_list_file:
            return False
            
        print("Loading server connection information...")
        try:
            # Try different encoding formats
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    self.server_df = pd.read_csv(self.server_list_file, encoding=encoding)
                    print(f"Successfully loaded server information using encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise Exception("Unable to read file with any encoding format")
            
            # Set column names
            self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir']
            print(f"Successfully loaded server information, total {len(self.server_df)} servers")
            return True
        except Exception as e:
            print(f"Error: Failed to load server information: {e}")
            return False
    
    def get_jar_info_from_server(self, server_info):
        """Get JAR file information from server"""
        try:
            # Create SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            ssh.connect(
                hostname=server_info['ip'],
                port=int(server_info['port']),
                username=server_info['username'],
                password=server_info['password'],
                timeout=30
            )
            
            # Execute ls command to get JAR file information
            jar_dir = server_info['jar_dir'].replace('\\', '/')
            command = f"ls -lah --block-size=1 --time-style='+%Y-%m-%d %H:%M:%S' {jar_dir} | grep '\\.jar$'"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if error:
                print(f"  Warning: {error.strip()}")
            
            # Parse output
            jar_files = self.parser.parse_ssh_output(output)
            return jar_files
            
        except Exception as e:
            print(f"  Connection failed: {e}")
            return []
    
    def load_all_data(self):
        """Load data for all services"""
        if self.server_list_file:
            return self.load_data_from_servers()
        elif self.data_dir:
            return self.load_data_from_files()
        else:
            print("Error: Must provide data_dir or server_list_file parameter")
            return False
    
    def load_data_from_servers(self):
        """Load data from servers"""
        if not self.load_server_data():
            return False
        
        total_servers = len(self.server_df)
        print(f"Found {total_servers} servers, starting to get JAR information...")
        
        for idx, (_, server_info) in enumerate(self.server_df.iterrows(), 1):
            # Handle NaN values in IP address
            ip_address = str(server_info['ip']) if pd.notna(server_info['ip']) else 'unknown'
            service_name = f"{server_info['service_name']}_{ip_address.replace('.', '_')}"
            
            print(f"[{idx}/{total_servers}] Getting service: {service_name} @ {ip_address}")
            
            # Check if server info has username and password
            if pd.isna(server_info['username']) or pd.isna(server_info['password']) or server_info['username'] == '' or server_info['password'] == '':
                print(f"  No username/password provided, treating as local directory: {server_info['jar_dir']}")
                jar_files = self.get_jar_info_from_local_dir(server_info['jar_dir'], service_name)
            else:
                jar_files = self.get_jar_info_from_server(server_info)
            
            self.services_data[service_name] = jar_files
            
            # Collect all JAR/class files
            for jar_info in jar_files:
                self.all_jars.add(jar_info['display_name'])
            
            # Show progress percentage
            progress = (idx / total_servers) * 100
            print(f"    Progress: {progress:.1f}% - Found {len(jar_files)} JAR/class files")
        
        print(f"\nData loading completed! Found {len(self.all_jars)} JAR/class files in total, distributed across {len(self.services_data)} services")
        return True
    
    def load_data_from_files(self):
        """Load data from files"""
        if not os.path.exists(self.data_dir):
            print(f"Error: Data directory {self.data_dir} does not exist")
            return False
        
        # Get all txt files
        txt_files = [f for f in os.listdir(self.data_dir) if f.endswith('.txt')]
        total_files = len(txt_files)
        
        print(f"Found {total_files} service files, starting to parse...")
        
        for idx, filename in enumerate(txt_files, 1):
            file_path = os.path.join(self.data_dir, filename)
            
            # Extract service name from filename
            service_name = self.extract_service_name(filename)
            
            print(f"[{idx}/{total_files}] Parsing service: {service_name} (file: {filename})")
            jar_files = self.parser.parse_file(file_path)
            
            self.services_data[service_name] = jar_files
            
            # Collect all JAR/class files
            for jar_info in jar_files:
                self.all_jars.add(jar_info['display_name'])
            
            # Show progress percentage
            progress = (idx / total_files) * 100
            print(f"    Progress: {progress:.1f}% - Found {len(jar_files)} JAR/class files")
        
        print(f"\nData loading completed! Found {len(self.all_jars)} JAR/class files in total, distributed across {len(self.services_data)} services")
        return True
    
    def find_latest_version(self, jar_name):
        """Find latest version information for specified JAR file"""
        latest_date = None
        latest_size = None
        
        # Traverse all services to find the latest modification date
        for service_jars in self.services_data.values():
            for jar_info in service_jars:
                if jar_info['display_name'] == jar_name:
                    if jar_info['modify_date'] and (latest_date is None or jar_info['modify_date'] > latest_date):
                        latest_date = jar_info['modify_date']
                        latest_size = jar_info['size']
        
        return latest_date, latest_size
    
    def is_latest_version(self, jar_info, latest_date, latest_size):
        """Check if JAR file is the latest version"""
        if not latest_size:
            return False
            
        # Only compare file size, same size means latest version
        return jar_info['size'] == latest_size
    
    def is_third_party_dependency(self, jar_filename):
        """Check if JAR file is a third-party dependency"""
        # Class files are always considered internal dependencies
        if jar_filename.endswith('.class'):
            return False
        
        # Check if JAR filename starts with any internal prefix
        for prefix in self.internal_prefixes:
            if jar_filename.lower().startswith(prefix.lower()):
                return False
        
        return True
    
    def _clean_column_name(self, name):
        """Clean column name, remove or replace invalid characters"""
        # Replace characters that may cause problems
        import re
        # First replace dots with _POINT_
        clean_name = re.sub(r'[.]', '_POINT_', name)
        # Replace hyphens with underscores
        clean_name = re.sub(r'[-]', '_', clean_name)
        # Replace other non-alphanumeric characters with underscores, but keep underscores themselves
        clean_name = re.sub(r'[^\w_]', '_', clean_name)
        # Ensure it doesn't start or end with underscores
        clean_name = clean_name.strip('_')
        if not clean_name:
            clean_name = 'unnamed'
        return clean_name
    
    def generate_report(self):
        """Generate analysis report"""
        if not self.services_data:
            print("Error: No data loaded")
            return None
    
    def get_jar_info_from_local_dir(self, jar_dir, service_name):
        """Get JAR file information from local directory"""
        try:
            if not os.path.exists(jar_dir):
                print(f"  Local directory does not exist: {jar_dir}")
                return []
            
            jar_files = []
            for filename in os.listdir(jar_dir):
                if filename.endswith('.jar'):
                    jar_path = os.path.join(jar_dir, filename)
                    try:
                        # Get file stats
                        stat = os.stat(jar_path)
                        size = stat.st_size
                        modify_time = stat.st_mtime
                        modify_date = datetime.fromtimestamp(modify_time)
                        
                        # Extract class name for .class files
                        display_name = filename
                        if filename.endswith('.class'):
                            class_name = self.parser.extract_class_name(filename)
                            if class_name:
                                display_name = class_name
                        
                        jar_files.append({
                            'filename': filename,
                            'display_name': display_name,
                            'size': size,
                            'modify_date': modify_date,
                            'date_str': modify_date.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except OSError as e:
                        print(f"  Error reading file {filename}: {e}")
                        continue
            
            print(f"  Found {len(jar_files)} JAR/class files in local directory")
            return jar_files
            
        except Exception as e:
            print(f"  Error reading local directory: {e}")
            return []
    
    def generate_report(self):
        """Generate analysis report"""
        if not self.services_data:
            print("Error: No data loaded")
            return None
            
        # Prepare service list (sorted alphabetically)
        services = sorted(self.services_data.keys())
        
        # Prepare data rows
        report_data = []
        total_jars = len(self.all_jars)
        
        print(f"Starting to generate report, need to process {total_jars} JAR/class files...")
        
        for idx, jar_name in enumerate(sorted(self.all_jars), 1):
            # Find latest version information for this JAR
            latest_date, latest_size = self.find_latest_version(jar_name)
            
            row_data = {
                'JAR_Filename': jar_name,
                'Third_Party_Dependency': 'Yes' if self.is_third_party_dependency(jar_name) else 'No'
            }
            
            # Add three columns for each service: size, last update date, is latest
            for service in services:
                service_jars = self.services_data[service]
                
                # Find this JAR in the service
                jar_found = None
                for jar_info in service_jars:
                    if jar_info['display_name'] == jar_name:
                        jar_found = jar_info
                        break
                
                # Clean service name to ensure valid column names
                clean_service_name = self._clean_column_name(service)
                
                if jar_found:
                    # This service has this JAR
                    row_data[f'{clean_service_name}_Size'] = jar_found['size']
                    row_data[f'{clean_service_name}_Last_Update_Date'] = jar_found['date_str']
                    
                    # Check if it's the latest version
                    if latest_date and latest_size:
                        is_latest = self.is_latest_version(jar_found, latest_date, latest_size)
                        row_data[f'{clean_service_name}_Is_Latest'] = 'Yes' if is_latest else 'No'
                    else:
                        row_data[f'{clean_service_name}_Is_Latest'] = 'Unknown'
                else:
                    # This service doesn't have this JAR
                    row_data[f'{clean_service_name}_Size'] = ''
                    row_data[f'{clean_service_name}_Last_Update_Date'] = ''
                    row_data[f'{clean_service_name}_Is_Latest'] = ''
            
            report_data.append(row_data)
            
            # Show progress every 100 JAR/class files
            if idx % 100 == 0 or idx == total_jars:
                progress = (idx / total_jars) * 100
                print(f"    Report generation progress: {progress:.1f}% ({idx}/{total_jars})")
        
        print("Report data generation completed!")
        return pd.DataFrame(report_data)


class CSVGenerator:
    """CSV report generator"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        
    def create_csv_report(self, output_file='jar_analysis_report.csv'):
        """Create CSV report"""
        print("Generating CSV report...")
        
        # Generate report data
        report_df = self.analyzer.generate_report()
        if report_df is None:
            return False
        
        print("Writing CSV file...")
        # Use pandas to write CSV
        report_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"CSV report generated: {output_file}")
        print(f"Total analyzed {len(report_df)} JAR/class files")
        print(f"Report contains {len(report_df.columns)} columns")
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='JAR package version analysis tool')
    parser.add_argument('--data-dir', 
                        help='JAR information file directory')
    parser.add_argument('--server-list-file', 
                        help='Server connection information CSV file')
    parser.add_argument('--internal-prefix-file', 
                        help='Internal dependency prefix file, one prefix per line')
    parser.add_argument('--output-file', default='work/output/jar_analysis_report.csv',
                        help='Output CSV filename (default: work/output/jar_analysis_report.csv)')
    parser.add_argument('--classes-dir', default='classes',
                        help='Classes directory name for .class file analysis (default: classes)')
    
    args = parser.parse_args()
    
    # Check parameters
    if not args.data_dir and not args.server_list_file:
        print("Error: Must provide --data-dir or --server-list-file parameter")
        return
    
    if args.data_dir and args.server_list_file:
        print("Error: --data-dir and --server-list-file parameters cannot be used together")
        return
    
    print("=== JAR Package Version Analysis Tool ===")
    if args.data_dir:
        print(f"Data directory: {args.data_dir}")
    if args.server_list_file:
        print(f"Server information file: {args.server_list_file}")
    print(f"Output file: {args.output_file}")
    print()
    
    # Create analyzer
    analyzer = JarAnalyzer(data_dir=args.data_dir, server_list_file=args.server_list_file, internal_prefix_file=args.internal_prefix_file, classes_dir=args.classes_dir)
    
    # Load data
    if not analyzer.load_all_data():
        return
    
    # Generate CSV report
    generator = CSVGenerator(analyzer)
    if generator.create_csv_report(args.output_file):
        print("\nAnalysis completed!")
        print("\nReport description:")
        print("- Each JAR file occupies one row")
        print("- Each service occupies three columns: size, last update date, is latest")
        print("- Column names include IP address and service name, dots in IP address replaced with underscores")
        print("- If a service doesn't have a JAR package, the corresponding columns are left empty")
    else:
        print("Report generation failed")


if __name__ == '__main__':
    main()
