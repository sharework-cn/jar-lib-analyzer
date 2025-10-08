#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JAR Files Information Import Script
Import JAR file information from info files or server commands to database
"""

import os
import sys
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import paramiko

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, JarFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JarInfoParser:
    """JAR file information parser"""
    
    def __init__(self):
        # Pattern to match ls -lah output for JAR files
        self.jar_pattern = re.compile(
            r'-rw[a-z-]*\s+\d+\s+\w+\s+\w+\s+(\d+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+(.+\.jar)$'
        )
    
    def parse_file(self, file_path):
        """Parse JAR information from file"""
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
                            
                            # Parse date time
                            modify_date = self._parse_date(date_str)
                            
                            jar_files.append({
                                'filename': filename,
                                'size': size,
                                'modify_date': modify_date,
                                'date_str': date_str
                            })
                break  # Successfully parsed
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Unable to read file {file_path} with any encoding format")
            
        return jar_files
    
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
                
                modify_date = self._parse_date(date_str)
                
                jar_files.append({
                    'filename': filename,
                    'size': size,
                    'modify_date': modify_date,
                    'date_str': date_str
                })
        
        return jar_files
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        try:
            # Try format with seconds first
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try format without seconds
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return None

class JarFileImporter:
    """JAR file information importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.parser = JarInfoParser()
        
        # Load internal dependency prefixes
        self.internal_prefixes = self._load_internal_prefixes()
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def _load_internal_prefixes(self):
        """Load internal dependency prefix list"""
        # Default internal dependency prefixes
        default_prefixes = [
            'dsop', 'jim', 'tsm', 'cmpp', 'card_market', 'cmft',
            'customer_service', 'cloud_encryptor', 'encryptor_', 'sim_',
            'smart_auth', 'sp_', 'student_card', 'tp-', 'tsn_'
        ]
        return default_prefixes
    
    def is_third_party_dependency(self, jar_filename):
        """Check if JAR file is a third-party dependency"""
        # Check if JAR filename starts with any internal prefix
        for prefix in self.internal_prefixes:
            if jar_filename.lower().startswith(prefix.lower()):
                return False
        return True
    
    def get_jar_info_from_server(self, service):
        """Get JAR file information from server"""
        try:
            # Create SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            ssh.connect(
                hostname=service.ip_address,
                port=service.port,
                username=service.username,
                password=service.password,
                timeout=30
            )
            
            # Execute ls command to get JAR file information
            jar_dir = service.jar_path.replace('\\', '/')
            command = f"ls -lah --block-size=1 --time-style='+%Y-%m-%d %H:%M:%S' {jar_dir} | grep '\\.jar$'"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if error:
                logger.warning(f"SSH command warning for {service.service_name}: {error.strip()}")
            
            # Parse output
            jar_files = self.parser.parse_ssh_output(output)
            return jar_files
            
        except Exception as e:
            logger.error(f"Connection failed for {service.service_name}: {e}")
            return []
    
    def get_jar_info_from_local_file(self, service):
        """Get JAR file information from local file"""
        jar_info_file_path = service.jar_info_file_path
        
        if not os.path.exists(jar_info_file_path):
            logger.warning(f"JAR info file not found: {jar_info_file_path}")
            return []
        
        return self.parser.parse_file(jar_info_file_path)
    
    def import_jar_files_for_service(self, service_name, environment='production'):
        """Import JAR files for a specific service"""
        logger.info(f"Importing JAR files for service: {service_name} ({environment})")
        
        db = self.get_db_session()
        
        try:
            # Get service information
            service = db.query(Service).filter(
                Service.service_name == service_name,
                Service.environment == environment
            ).first()
            
            if not service:
                logger.error(f"Service not found: {service_name} ({environment})")
                return False
            
            # Get JAR file information
            if service.username and service.password:
                # Get from server
                jar_files_info = self.get_jar_info_from_server(service)
            else:
                # Get from local file
                jar_files_info = self.get_jar_info_from_local_file(service)
            
            if not jar_files_info:
                logger.warning(f"No JAR files found for service: {service_name}")
                return True
            
            imported_count = 0
            updated_count = 0
            
            for jar_info in jar_files_info:
                try:
                    # Check if JAR file already exists
                    existing_jar = db.query(JarFile).filter(
                        JarFile.service_id == service.id,
                        JarFile.jar_name == jar_info['filename']
                    ).first()
                    
                    # Determine if it's a third-party dependency
                    is_third_party = self.is_third_party_dependency(jar_info['filename'])
                    
                    if existing_jar:
                        # Update existing JAR file
                        existing_jar.file_size = jar_info['size']
                        existing_jar.last_modified = jar_info['modify_date']
                        existing_jar.is_third_party = is_third_party
                        updated_count += 1
                        logger.debug(f"Updated JAR: {jar_info['filename']}")
                    else:
                        # Create new JAR file record
                        jar_file = JarFile(
                            service_id=service.id,
                            jar_name=jar_info['filename'],
                            file_size=jar_info['size'],
                            last_modified=jar_info['modify_date'],
                            is_third_party=is_third_party,
                            is_latest=False  # Will be determined later
                        )
                        db.add(jar_file)
                        imported_count += 1
                        logger.debug(f"Imported JAR: {jar_info['filename']}")
                    
                    db.commit()
                    
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"JAR file already exists: {jar_info['filename']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error importing JAR {jar_info['filename']}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new JAR files, updated {updated_count} existing JAR files for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing JAR files for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def import_jar_files_for_all_services(self):
        """Import JAR files for all services"""
        logger.info("Importing JAR files for all services")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            for idx, service in enumerate(services, 1):
                logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                
                success = self.import_jar_files_for_service(service.service_name, service.environment)
                if not success:
                    logger.error(f"Failed to import JAR files for service: {service.service_name}")
                
                # Show progress
                progress = (idx / total_services) * 100
                logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("JAR files import completed for all services")
            
        except Exception as e:
            logger.error(f"Error importing JAR files for all services: {e}")
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Import JAR file information to database')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Import JAR files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Import JAR files for all services')
    
    args = parser.parse_args()
    
    importer = JarFileImporter(args.database_url)
    
    try:
        if args.all_services:
            importer.import_jar_files_for_all_services()
        elif args.service_name:
            importer.import_jar_files_for_service(args.service_name, args.environment)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("JAR files import completed successfully!")
        
    except Exception as e:
        logger.error(f"JAR files import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
