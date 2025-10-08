#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JAR File Decompiler Tool
Fetch specified JAR files from multiple servers, decompile them for subsequent comparison analysis
"""

import os
import sys
import pandas as pd
import argparse
import subprocess
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko
from scp import SCPClient


class JarComparisonTool:
    """JAR/Class file decompiler tool"""
    
    def __init__(self, file_name, analysis_csv, server_list_file, output_dir, file_type="jar"):
        self.file_name = file_name
        self.analysis_csv = analysis_csv
        self.server_list_file = server_list_file
        self.output_dir = output_dir
        self.file_type = file_type  # "jar" or "class"
        self.cfr_jar = "assets/jar/cfr-0.152.jar"
        
        # Create output directories
        self._create_output_directories()
        
    def _create_output_directories(self):
        """Create output directory structure"""
        # Create main output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        if self.file_type == "jar":
            # Create JAR file storage directory
            self.file_dir = os.path.join(self.output_dir, "_jar")
            self.decompile_dir = self.output_dir  # Direct output to main directory
        else:  # class
            # Create class file storage directory
            self.file_dir = os.path.join(self.output_dir, "_class")
            self.decompile_dir = self.output_dir  # Direct output to main directory
        
        os.makedirs(self.file_dir, exist_ok=True)
        os.makedirs(self.decompile_dir, exist_ok=True)
        
        print(f"Output directory created: {self.output_dir}")
        print(f"File storage directory: {self.file_dir}")
        print(f"Decompile directory: {self.decompile_dir}")
    
    def load_analysis_data(self):
        """Load JAR analysis result data"""
        print("Loading JAR analysis results...")
        try:
            # Try different encoding formats
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    self.analysis_df = pd.read_csv(self.analysis_csv, encoding=encoding)
                    print(f"Successfully loaded analysis results using encoding {encoding}, total {len(self.analysis_df)} rows")
                    return True
                except UnicodeDecodeError:
                    continue
            else:
                raise Exception("Unable to read analysis result file with any encoding format")
        except Exception as e:
            print(f"Error: Failed to load analysis results: {e}")
            return False
    
    def load_server_data(self):
        """Load server connection information"""
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
            
            # Set column names - support multiple formats
            if len(self.server_df.columns) == 6:
                # Old format: ip, port, username, password, service_name, jar_dir
                self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir']
                # Add empty columns for backward compatibility
                self.server_df['server_base_path'] = ''
                self.server_df['class_dir'] = ''
                self.server_df['source_path'] = ''
            elif len(self.server_df.columns) == 7:
                # Check if it's the custom format by looking at the actual column names
                if 'server_name' in str(self.server_df.columns[4]).lower():
                    # Custom format: ip, port, user, pswd, server_name, jar_path, classes_path
                    self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir', 'class_dir']
                    # Add empty columns for backward compatibility
                    self.server_df['server_base_path'] = ''
                    self.server_df['source_path'] = ''
                else:
                    # New format: ip, port, username, password, service_name, jar_dir, class_dir
                    self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir', 'class_dir']
                    # Add empty columns for backward compatibility
                    self.server_df['server_base_path'] = ''
                    self.server_df['source_path'] = ''
            elif len(self.server_df.columns) == 9:
                # New format: ip, port, username, password, service_name, server_base_path, jar_path, classes_path, source_path
                self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'server_base_path', 'jar_dir', 'class_dir', 'source_path']
            else:
                raise Exception(f"Invalid server information file format. Expected 6, 7, or 9 columns, got {len(self.server_df.columns)}")
            
            print(f"Successfully loaded server information, total {len(self.server_df)} servers")
            return True
        except Exception as e:
            print(f"Error: Failed to load server information: {e}")
            return False
    
    def find_file_locations(self):
        """Find file locations from analysis results"""
        # Check if file_name is a service name (contains no dots or contains service-like patterns)
        if self._is_service_name(self.file_name):
            return self._find_service_files()
        else:
            return self._find_single_file_locations()
    
    def _is_service_name(self, name):
        """Check if the given name is a service name rather than a file name"""
        # If it contains dots and looks like a class name or JAR name, it's a file
        if '.' in name and (name.endswith('.jar') or name.endswith('.class') or '/' in name):
            return False
        
        # If it's a simple name without dots, it's likely a service name
        if '.' not in name:
            return True
        
        # If it contains dots but doesn't look like a file, it might be a service name
        # Check if it matches any service patterns in the analysis data
        for col in self.analysis_df.columns:
            if col.endswith('_Size'):
                service_key = col.replace('_Size', '')
                service_name = self._extract_service_name_from_key(service_key)
                if service_name == name:
                    return True
        
        return False
    
    def _extract_service_name_from_key(self, service_key):
        """Extract service name from service key"""
        if '_' in service_key:
            parts = service_key.split('_')
            # Find IP address part (last 4 parts)
            if len(parts) >= 5:
                # Check if last 4 parts form a valid IP address
                ip_parts = parts[-4:]
                if all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                    service_name = '_'.join(parts[:-4])
                else:
                    # No valid IP address found, treat as service name only
                    service_name = service_key
            else:
                # No valid IP address found, treat as service name only
                service_name = service_key
        else:
            # No underscore, treat as service name only
            service_name = service_key
        
        # Restore dots in service name (replace _POINT_ back to .)
        service_name = service_name.replace('_POINT_', '.')
        return service_name
    
    def _find_service_files(self):
        """Find all non-third-party files for a specific service"""
        print(f"Looking for all non-third-party {self.file_type.upper()} files for service '{self.file_name}'...")
        
        locations = []
        target_service = self.file_name
        
        # Find all files that belong to this service and are not third-party dependencies
        for _, row in self.analysis_df.iterrows():
            file_name = row['JAR_Filename']
            is_third_party = row.get('Third_Party_Dependency', 'No') == 'Yes'
            
            # Skip third-party dependencies
            if is_third_party:
                continue
            
            # Check if this file exists in the target service
            for col in self.analysis_df.columns:
                if col.endswith('_Size') and not pd.isna(row[col]) and row[col] != '':
                    service_key = col.replace('_Size', '')
                    service_name = self._extract_service_name_from_key(service_key)
                    
                    if service_name == target_service:
                        # Extract IP address
                        if '_' in service_key:
                            parts = service_key.split('_')
                            if len(parts) >= 5:
                                ip_parts = parts[-4:]
                                if all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                                    ip_address = '.'.join(ip_parts)
                                else:
                                    ip_address = 'local'
                            else:
                                ip_address = 'local'
                        else:
                            ip_address = 'local'
                        
                        locations.append({
                            'file_name': file_name,
                            'service_name': service_name,
                            'ip_address': ip_address,
                            'service_key': service_key
                        })
                        break
        
        print(f"Found {len(locations)} non-third-party {self.file_type.upper()} files for service '{target_service}'")
        for loc in locations:
            print(f"  - {loc['file_name']} @ {loc['service_name']}@{loc['ip_address']}")
        
        return locations
    
    def _find_single_file_locations(self):
        """Find locations for a single file (original behavior)"""
        print(f"Looking for {self.file_type.upper()} file '{self.file_name}' locations...")
        
        # Find row containing this file
        file_row = self.analysis_df[self.analysis_df['JAR_Filename'] == self.file_name]
        
        if file_row.empty:
            print(f"Error: {self.file_type.upper()} file '{self.file_name}' not found")
            return []
        
        locations = []
        file_info = file_row.iloc[0]
        
        # Traverse all columns to find services containing this file
        for col in self.analysis_df.columns:
            if col.endswith('_Size') and not pd.isna(file_info[col]) and file_info[col] != '':
                # Extract service name and IP address
                service_key = col.replace('_Size', '')
                service_name = self._extract_service_name_from_key(service_key)
                
                # Extract IP address
                if '_' in service_key:
                    parts = service_key.split('_')
                    if len(parts) >= 5:
                        ip_parts = parts[-4:]
                        if all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                            ip_address = '.'.join(ip_parts)
                        else:
                            ip_address = 'local'
                    else:
                        ip_address = 'local'
                else:
                    ip_address = 'local'
                
                locations.append({
                    'file_name': self.file_name,
                    'service_name': service_name,
                    'ip_address': ip_address,
                    'service_key': service_key
                })
        
        print(f"Found {len(locations)} locations containing this {self.file_type.upper()} file")
        for loc in locations:
            print(f"  - {loc['service_name']} @ {loc['ip_address']}")
        
        return locations
    
    def get_server_info(self, ip_address, service_name):
        """Get server connection information based on IP address and service name"""
        # If IP address is 'local', match by service name only
        if ip_address == 'local':
            server_info = self.server_df[self.server_df['service_name'] == service_name]
        else:
            # Find server info by both IP and service name
            server_info = self.server_df[
                (self.server_df['ip'] == ip_address) & 
                (self.server_df['service_name'] == service_name)
            ]
        
        if server_info.empty:
            return None
        
        return server_info.iloc[0]
    
    def _replace_path_variables(self, path_template, service_name, server_base_path):
        """Replace {service_name} and {server_base_path} variables in path template"""
        if pd.isna(path_template) or path_template == '':
            return ''
        
        # Replace variables
        path = path_template.replace('{service_name}', service_name)
        path = path.replace('{server_base_path}', server_base_path)
        
        return path
    
    def download_file(self, location, server_info):
        """Download file from server or copy from local directory"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        service_key = location['service_key']
        file_name = location.get('file_name', self.file_name)
        
        # Check if server info has username and password
        if pd.isna(server_info['username']) or pd.isna(server_info['password']) or server_info['username'] == '' or server_info['password'] == '':
            print(f"Copying {self.file_type.upper()} file '{file_name}' from local directory for {service_name}...")
            return self.copy_file_from_local(location, server_info)
        else:
            print(f"Downloading {self.file_type.upper()} file '{file_name}' from {ip_address} for {service_name}...")
            return self.download_file_from_server(location, server_info)
    
    def copy_file_from_local(self, location, server_info):
        """Copy file from local directory"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        file_name = location.get('file_name', self.file_name)
        
        try:
            # Get server_base_path for variable replacement
            server_base_path = server_info.get('server_base_path', '')
            
            # Build local file path
            if self.file_type == "class":
                # Convert class name to file path
                class_file_path = file_name.replace('.', '/') + '.class'
                
                # Check if class_dir is specified and replace variables
                if pd.notna(server_info['class_dir']) and server_info['class_dir'] != '':
                    # Use specified class directory with variable replacement
                    class_dir = self._replace_path_variables(server_info['class_dir'], service_name, server_base_path)
                    local_file_path = os.path.join(class_dir, class_file_path)
                else:
                    # Try different possible paths for class files (backward compatibility)
                    jar_dir = self._replace_path_variables(server_info['jar_dir'], service_name, server_base_path)
                    possible_paths = [
                        os.path.join(jar_dir, class_file_path),  # Direct path
                        os.path.join(jar_dir, 'classes', class_file_path),  # With classes dir
                        os.path.join(jar_dir, 'WEB-INF', 'classes', class_file_path),  # With WEB-INF/classes
                    ]
                    
                    # Find the first existing path
                    local_file_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            local_file_path = path
                            break
                    
                    if local_file_path is None:
                        # If no path exists, use the first one as default
                        local_file_path = possible_paths[0]
            else:
                # For JAR files, replace variables in jar_dir and use filename directly
                jar_dir = self._replace_path_variables(server_info['jar_dir'], service_name, server_base_path)
                local_file_path = os.path.join(jar_dir, file_name)
            
            if not os.path.exists(local_file_path):
                print(f"  Local {self.file_type.upper()} file does not exist: {local_file_path}")
                return None
            
            # Create local directory
            local_service_dir = os.path.join(self.file_dir, f"{service_name}@{ip_address}").replace('\\', '/')
            os.makedirs(local_service_dir, exist_ok=True)
            
            # Copy file
            if self.file_type == "class":
                # For class files, ensure .class extension is preserved
                target_file_path = os.path.join(local_service_dir, file_name + '.class')
            else:
                target_file_path = os.path.join(local_service_dir, file_name)
            shutil.copy2(local_file_path, target_file_path)
            
            print(f"  Successfully copied: {target_file_path}")
            return target_file_path
            
        except Exception as e:
            print(f"  Copy failed: {e}")
            return None
    
    def download_file_from_server(self, location, server_info):
        """Download file from server via SSH/SCP"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        file_name = location.get('file_name', self.file_name)
        
        try:
            # Create SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            ssh.connect(
                hostname=ip_address,
                port=int(server_info['port']),
                username=server_info['username'],
                password=server_info['password'],
                timeout=30
            )
            
            # Build remote file path (use forward slashes as this is Linux path)
            server_base_path = server_info.get('server_base_path', '')
            jar_dir = self._replace_path_variables(server_info['jar_dir'], service_name, server_base_path)
            remote_file_path = jar_dir.replace('\\', '/') + '/' + file_name
            
            # Create local directory
            local_service_dir = os.path.join(self.file_dir, f"{service_name}@{ip_address}").replace('\\', '/')
            os.makedirs(local_service_dir, exist_ok=True)
            
            # Download file
            if self.file_type == "class":
                # For class files, ensure .class extension is preserved
                local_file_path = os.path.join(local_service_dir, file_name + '.class')
            else:
                local_file_path = os.path.join(local_service_dir, file_name)
            
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_file_path, local_file_path)
            
            ssh.close()
            
            print(f"  Successfully downloaded: {local_file_path}")
            return local_file_path
            
        except Exception as e:
            print(f"  Download failed: {e}")
            return None
    
    def decompile_file(self, file_path, service_name, ip_address, file_info=None, file_name=None):
        """Decompile JAR or class file"""
        if file_name is None:
            file_name = self.file_name
        
        print(f"Decompiling {self.file_type.upper()} file '{file_name}' for {service_name}@{ip_address}...")
        
        try:
            # Create decompile output directory
            if file_info and file_info.get('modify_date'):
                # Use file's last update date (date only, no time)
                date_str = file_info['modify_date'].strftime("%Y%m%d")
            else:
                # Use current date as fallback
                date_str = datetime.now().strftime("%Y%m%d")
            
            if self.file_type == "jar":
                # For JAR files, create subdirectory with JAR filename
                jar_name_without_ext = file_name.replace('.jar', '')
                decompile_dir = os.path.join(self.decompile_dir, jar_name_without_ext, f"{date_str}-{service_name}@{ip_address}").replace('\\', '/')
            else:
                # For class files, use class name as subdirectory
                class_name = file_name.replace('.class', '').replace('/', '.')
                decompile_dir = os.path.join(self.decompile_dir, class_name, f"{date_str}-{service_name}@{ip_address}").replace('\\', '/')
            
            os.makedirs(decompile_dir, exist_ok=True)
            
            # Execute decompile command
            command = [
                'java', '-jar', self.cfr_jar,
                file_path,
                '--outputdir', decompile_dir
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"  Decompilation successful: {decompile_dir}")
                return decompile_dir
            else:
                print(f"  Decompilation failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"  Decompilation failed: {e}")
            return None
    
    def process_file_locations(self, locations):
        """Process all file locations"""
        print(f"Starting to process {len(locations)} {self.file_type.upper()} file locations...")
        
        successful_downloads = []
        
        # Use thread pool for parallel downloads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for location in locations:
                server_info = self.get_server_info(location['ip_address'], location['service_name'])
                if server_info is not None:
                    future = executor.submit(self.download_file, location, server_info)
                    futures.append((future, location))
                else:
                    print(f"Warning: Server information not found {location['ip_address']} - {location['service_name']}")
            
            # Wait for downloads to complete
            for future, location in futures:
                try:
                    file_path = future.result()
                    if file_path:
                        # Get file information for decompilation
                        file_info = self.get_file_info_from_analysis(location)
                        successful_downloads.append((file_path, location, file_info))
                except Exception as e:
                    print(f"Download exception: {e}")
        
        print(f"Successfully downloaded {len(successful_downloads)} {self.file_type.upper()} files")
        
        # Decompile all downloaded files
        print("Starting decompilation...")
        for file_path, location, file_info in successful_downloads:
            file_name = location.get('file_name', self.file_name)
            self.decompile_file(file_path, location['service_name'], location['ip_address'], file_info, file_name)
        
        print("Processing completed!")
    
    def get_file_info_from_analysis(self, location):
        """Get file information from analysis results"""
        try:
            file_name = location.get('file_name', self.file_name)
            
            # Find row containing this file
            file_row = self.analysis_df[self.analysis_df['JAR_Filename'] == file_name]
            
            if file_row.empty:
                return None
            
            file_info = file_row.iloc[0]
            
            # Find corresponding service columns
            service_key = location['service_key']
            size_col = f"{service_key}_Size"
            date_col = f"{service_key}_Last_Update_Date"
            
            if size_col in file_info and date_col in file_info:
                size = file_info[size_col]
                date_str = file_info[date_col]
                
                # Parse date time (try both formats: with and without seconds)
                modify_date = None
                if pd.notna(date_str) and date_str != '':
                    try:
                        modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            pass
                
                return {
                    'filename': file_name,
                    'size': size,
                    'modify_date': modify_date,
                    'date_str': date_str
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to get {self.file_type.upper()} information: {e}")
            return None
    
    def run(self):
        """Run main process"""
        print("=== JAR/Class File Decompiler Tool ===")
        print(f"Target {self.file_type.upper()} file: {self.file_name}")
        print(f"Analysis result file: {self.analysis_csv}")
        print(f"Server information file: {self.server_list_file}")
        print(f"Output directory: {self.output_dir}")
        print()
        
        # Check if CFR tool exists
        if not os.path.exists(self.cfr_jar):
            print(f"Error: CFR tool does not exist: {self.cfr_jar}")
            return False
        
        # Load data
        if not self.load_analysis_data():
            return False
        
        if not self.load_server_data():
            return False
        
        # Find file locations
        locations = self.find_file_locations()
        if not locations:
            return False
        
        # Process all locations
        self.process_file_locations(locations)
        
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='JAR/Class file decompiler tool')
    parser.add_argument('file_name', help='JAR or class filename to decompile')
    parser.add_argument('--analysis-csv', required=True, help='JAR/Class analysis result CSV file')
    parser.add_argument('--server-list-file', required=True, help='Server connection information CSV file')
    parser.add_argument('--output-dir', help='Output directory (default: work/{file_name})')
    parser.add_argument('--file-type', choices=['jar', 'class'], default='jar', help='File type: jar or class (default: jar)')
    
    args = parser.parse_args()
    
    # Set default output directory
    if not args.output_dir:
        # Remove extension as directory name
        file_name_without_ext = args.file_name.replace('.jar', '').replace('.class', '')
        args.output_dir = f"work/{file_name_without_ext}"
    
    # Create tool instance and run
    tool = JarComparisonTool(
        file_name=args.file_name,
        analysis_csv=args.analysis_csv,
        server_list_file=args.server_list_file,
        output_dir=args.output_dir,
        file_type=args.file_type
    )
    
    success = tool.run()
    
    if success:
        print("\nTool execution completed!")
        print(f"Output directory: {args.output_dir}")
        print("Directory structure:")
        if args.file_type == "jar":
            print("  - _jar/ : Original JAR files")
            print("  - {jar_name}/{timestamp}-{service}@{ip}/ : JAR decompilation results")
        else:
            print("  - _class/ : Original class files")
            print("  - {class_name}/{timestamp}-{service}@{ip}/ : Class decompilation results")
    else:
        print("\nTool execution failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
