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
    """JAR file decompiler tool"""
    
    def __init__(self, jar_name, analysis_csv, server_list_file, output_dir):
        self.jar_name = jar_name
        self.analysis_csv = analysis_csv
        self.server_list_file = server_list_file
        self.output_dir = output_dir
        self.cfr_jar = "assets/jar/cfr-0.152.jar"
        
        # Create output directories
        self._create_output_directories()
        
    def _create_output_directories(self):
        """Create output directory structure"""
        # Create main output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create JAR file storage directory
        self.jar_dir = os.path.join(self.output_dir, "_jar")
        os.makedirs(self.jar_dir, exist_ok=True)
        
        print(f"Output directory created: {self.output_dir}")
        print(f"JAR file directory: {self.jar_dir}")
    
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
            
            # Set column names
            self.server_df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir']
            print(f"Successfully loaded server information, total {len(self.server_df)} servers")
            return True
        except Exception as e:
            print(f"Error: Failed to load server information: {e}")
            return False
    
    def find_jar_locations(self):
        """Find JAR file locations from analysis results"""
        print(f"Looking for JAR file '{self.jar_name}' locations...")
        
        # Find row containing this JAR file
        jar_row = self.analysis_df[self.analysis_df['JAR_Filename'] == self.jar_name]
        
        if jar_row.empty:
            print(f"Error: JAR file '{self.jar_name}' not found")
            return []
        
        locations = []
        jar_info = jar_row.iloc[0]
        
        # Traverse all columns to find services containing this JAR file
        for col in self.analysis_df.columns:
            if col.endswith('_Size') and not pd.isna(jar_info[col]) and jar_info[col] != '':
                # Extract service name and IP address
                service_key = col.replace('_Size', '')
                # Service name format: service_name_IP_address
                if '_' in service_key:
                    parts = service_key.split('_')
                    # Find IP address part (last 4 parts)
                    if len(parts) >= 5:
                        # Check if last 4 parts form a valid IP address
                        ip_parts = parts[-4:]
                        if all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                            service_name = '_'.join(parts[:-4])
                            ip_address = '.'.join(ip_parts)
                        else:
                            # Handle case where IP is not in standard format
                            # Try to find IP-like pattern or use the last part as IP
                            service_name = '_'.join(parts[:-1])
                            ip_address = parts[-1]
                    else:
                        # Handle case with fewer parts
                        service_name = parts[0] if parts else service_key
                        ip_address = parts[-1] if len(parts) > 1 else 'unknown'
                    
                    # Restore dots in service name (replace _POINT_ back to .)
                    service_name = service_name.replace('_POINT_', '.')
                    
                    locations.append({
                        'service_name': service_name,
                        'ip_address': ip_address,
                        'service_key': service_key
                    })
        
        print(f"Found {len(locations)} locations containing this JAR file")
        for loc in locations:
            print(f"  - {loc['service_name']} @ {loc['ip_address']}")
        
        return locations
    
    def get_server_info(self, ip_address, service_name):
        """Get server connection information based on IP address and service name"""
        # Find server info by both IP and service name
        server_info = self.server_df[
            (self.server_df['ip'] == ip_address) & 
            (self.server_df['service_name'] == service_name)
        ]
        
        if server_info.empty:
            return None
        
        return server_info.iloc[0]
    
    def download_jar_file(self, location, server_info):
        """Download JAR file from server or copy from local directory"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        service_key = location['service_key']
        
        # Check if server info has username and password
        if pd.isna(server_info['username']) or pd.isna(server_info['password']) or server_info['username'] == '' or server_info['password'] == '':
            print(f"Copying JAR file from local directory for {service_name}...")
            return self.copy_jar_from_local(location, server_info)
        else:
            print(f"Downloading JAR file from {ip_address} for {service_name}...")
            return self.download_jar_from_server(location, server_info)
    
    def copy_jar_from_local(self, location, server_info):
        """Copy JAR file from local directory"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        
        try:
            # Build local file path
            local_jar_path = os.path.join(server_info['jar_dir'], self.jar_name)
            
            if not os.path.exists(local_jar_path):
                print(f"  Local JAR file does not exist: {local_jar_path}")
                return None
            
            # Create local directory
            local_service_dir = os.path.join(self.jar_dir, f"{service_name}@{ip_address}")
            os.makedirs(local_service_dir, exist_ok=True)
            
            # Copy file
            target_jar_path = os.path.join(local_service_dir, self.jar_name)
            shutil.copy2(local_jar_path, target_jar_path)
            
            print(f"  Successfully copied: {target_jar_path}")
            return target_jar_path
            
        except Exception as e:
            print(f"  Copy failed: {e}")
            return None
    
    def download_jar_from_server(self, location, server_info):
        """Download JAR file from server via SSH/SCP"""
        service_name = location['service_name']
        ip_address = location['ip_address']
        
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
            remote_jar_path = server_info['jar_dir'].replace('\\', '/') + '/' + self.jar_name
            
            # Create local directory
            local_service_dir = os.path.join(self.jar_dir, f"{service_name}@{ip_address}")
            os.makedirs(local_service_dir, exist_ok=True)
            
            # Download file
            local_jar_path = os.path.join(local_service_dir, self.jar_name)
            
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_jar_path, local_jar_path)
            
            ssh.close()
            
            print(f"  Successfully downloaded: {local_jar_path}")
            return local_jar_path
            
        except Exception as e:
            print(f"  Download failed: {e}")
            return None
    
    def decompile_jar(self, jar_path, service_name, ip_address, jar_info=None):
        """Decompile JAR file"""
        print(f"Decompiling JAR file for {service_name}@{ip_address}...")
        
        try:
            # Create decompile output directory
            if jar_info and jar_info.get('modify_date'):
                # Use JAR file's last update date (date only, no time)
                date_str = jar_info['modify_date'].strftime("%Y%m%d")
            else:
                # Use current date as fallback
                date_str = datetime.now().strftime("%Y%m%d")
            
            decompile_dir = os.path.join(self.output_dir, f"{date_str}-{service_name}@{ip_address}")
            os.makedirs(decompile_dir, exist_ok=True)
            
            # Execute decompile command
            command = [
                'java', '-jar', self.cfr_jar,
                jar_path,
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
    
    def process_jar_locations(self, locations):
        """Process all JAR file locations"""
        print(f"Starting to process {len(locations)} JAR file locations...")
        
        successful_downloads = []
        
        # Use thread pool for parallel downloads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for location in locations:
                server_info = self.get_server_info(location['ip_address'], location['service_name'])
                if server_info is not None:
                    future = executor.submit(self.download_jar_file, location, server_info)
                    futures.append((future, location))
                else:
                    print(f"Warning: Server information not found {location['ip_address']} - {location['service_name']}")
            
            # Wait for downloads to complete
            for future, location in futures:
                try:
                    jar_path = future.result()
                    if jar_path:
                        # Get JAR file information for decompilation
                        jar_info = self.get_jar_info_from_analysis(location)
                        successful_downloads.append((jar_path, location, jar_info))
                except Exception as e:
                    print(f"Download exception: {e}")
        
        print(f"Successfully downloaded {len(successful_downloads)} JAR files")
        
        # Decompile all downloaded JAR files
        print("Starting decompilation...")
        for jar_path, location, jar_info in successful_downloads:
            self.decompile_jar(jar_path, location['service_name'], location['ip_address'], jar_info)
        
        print("Processing completed!")
    
    def get_jar_info_from_analysis(self, location):
        """Get JAR file information from analysis results"""
        try:
            # Find row containing this JAR file
            jar_row = self.analysis_df[self.analysis_df['JAR_Filename'] == self.jar_name]
            
            if jar_row.empty:
                return None
            
            jar_info = jar_row.iloc[0]
            
            # Find corresponding service columns
            service_key = location['service_key']
            size_col = f"{service_key}_Size"
            date_col = f"{service_key}_Last_Update_Date"
            
            if size_col in jar_info and date_col in jar_info:
                size = jar_info[size_col]
                date_str = jar_info[date_col]
                
                # Parse date time
                modify_date = None
                if pd.notna(date_str) and date_str != '':
                    try:
                        modify_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
                
                return {
                    'filename': self.jar_name,
                    'size': size,
                    'modify_date': modify_date,
                    'date_str': date_str
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to get JAR information: {e}")
            return None
    
    def run(self):
        """Run main process"""
        print("=== JAR File Decompiler Tool ===")
        print(f"Target JAR file: {self.jar_name}")
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
        
        # Find JAR file locations
        locations = self.find_jar_locations()
        if not locations:
            return False
        
        # Process all locations
        self.process_jar_locations(locations)
        
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='JAR file decompiler tool')
    parser.add_argument('jar_name', help='JAR filename to decompile')
    parser.add_argument('--analysis-csv', required=True, help='JAR analysis result CSV file')
    parser.add_argument('--server-list-file', required=True, help='Server connection information CSV file')
    parser.add_argument('--output-dir', help='Output directory (default: work/{jar_name})')
    
    args = parser.parse_args()
    
    # Set default output directory
    if not args.output_dir:
        # Remove .jar extension as directory name
        jar_name_without_ext = args.jar_name.replace('.jar', '')
        args.output_dir = f"work/{jar_name_without_ext}"
    
    # Create tool instance and run
    tool = JarComparisonTool(
        jar_name=args.jar_name,
        analysis_csv=args.analysis_csv,
        server_list_file=args.server_list_file,
        output_dir=args.output_dir
    )
    
    success = tool.run()
    
    if success:
        print("\nTool execution completed!")
        print(f"Output directory: {args.output_dir}")
        print("Directory structure:")
        print("  - _jar/ : Original JAR files")
        print("  - {timestamp}-{service}@{ip}/ : Decompilation results")
    else:
        print("\nTool execution failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
