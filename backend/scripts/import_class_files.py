#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class Files Information Import Script
Import class file information from info files or server commands to database
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

from main import Service, ClassFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClassInfoParser:
    """Class file information parser"""
    
    def __init__(self, classes_dir="classes"):
        # Pattern to match ls -lah output for class files
        self.class_pattern = re.compile(
            r'-rw[a-z-]*\s+\d+\s+\w+\s+\w+\s+(\d+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+(.+\.class)$'
        )
        self.classes_dir = classes_dir
    
    def parse_file(self, file_path):
        """Parse class information from file"""
        class_files = []
        
        # Try different encoding formats
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        match = self.class_pattern.match(line)
                        if match:
                            size = int(match.group(1))
                            date_str = match.group(2)
                            filename = match.group(3)
                            
                            # Parse date time
                            modify_date = self._parse_date(date_str)
                            
                            # Extract class full name from file path
                            class_full_name = self.extract_class_name(filename)
                            
                            if class_full_name:
                                class_files.append({
                                    'filename': filename,
                                    'class_full_name': class_full_name,
                                    'size': size,
                                    'modify_date': modify_date,
                                    'date_str': date_str
                                })
                break  # Successfully parsed
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Unable to read file {file_path} with any encoding format")
            
        return class_files
    
    def parse_ssh_output(self, output):
        """Parse SSH command output"""
        class_files = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            match = self.class_pattern.match(line)
            if match:
                size = int(match.group(1))
                date_str = match.group(2)
                filename = match.group(3)
                
                modify_date = self._parse_date(date_str)
                
                # Extract class full name from file path
                class_full_name = self.extract_class_name(filename)
                
                if class_full_name:
                    class_files.append({
                        'filename': filename,
                        'class_full_name': class_full_name,
                        'size': size,
                        'modify_date': modify_date,
                        'date_str': date_str
                    })
        
        return class_files
    
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

class ClassFileImporter:
    """Class file information importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.parser = ClassInfoParser()
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def get_class_info_from_server(self, service):
        """Get class file information from server"""
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
            
            # Execute find command to get class file information
            classes_path = service.classes_path.replace('\\', '/')
            command = f"find {classes_path} -name '*.class' -exec ls -lah --block-size=1 --time-style='+%Y-%m-%d %H:%M:%S' {{}} \\;"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if error:
                logger.warning(f"SSH command warning for {service.service_name}: {error.strip()}")
            
            # Parse output
            class_files = self.parser.parse_ssh_output(output)
            return class_files
            
        except Exception as e:
            logger.error(f"Connection failed for {service.service_name}: {e}")
            return []
    
    def get_class_info_from_local_file(self, service):
        """Get class file information from local file"""
        class_info_file_path = service.class_info_file_path
        
        if not os.path.exists(class_info_file_path):
            logger.warning(f"Class info file not found: {class_info_file_path}")
            return []
        
        return self.parser.parse_file(class_info_file_path)
    
    def import_class_files_for_service(self, service_name, environment='production'):
        """Import class files for a specific service"""
        logger.info(f"Importing class files for service: {service_name} ({environment})")
        
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
            
            # Get class file information
            if service.username and service.password:
                # Get from server
                class_files_info = self.get_class_info_from_server(service)
            else:
                # Get from local file
                class_files_info = self.get_class_info_from_local_file(service)
            
            if not class_files_info:
                logger.warning(f"No class files found for service: {service_name}")
                return True
            
            imported_count = 0
            updated_count = 0
            
            for class_info in class_files_info:
                try:
                    # Check if class file already exists
                    existing_class = db.query(ClassFile).filter(
                        ClassFile.service_id == service.id,
                        ClassFile.class_full_name == class_info['class_full_name']
                    ).first()
                    
                    if existing_class:
                        # Update existing class file
                        existing_class.file_size = class_info['size']
                        existing_class.last_modified = class_info['modify_date']
                        updated_count += 1
                        logger.debug(f"Updated class: {class_info['class_full_name']}")
                    else:
                        # Create new class file record
                        class_file = ClassFile(
                            service_id=service.id,
                            class_full_name=class_info['class_full_name'],
                            file_size=class_info['size'],
                            last_modified=class_info['modify_date']
                        )
                        db.add(class_file)
                        imported_count += 1
                        logger.debug(f"Imported class: {class_info['class_full_name']}")
                    
                    db.commit()
                    
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"Class file already exists: {class_info['class_full_name']}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error importing class {class_info['class_full_name']}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new class files, updated {updated_count} existing class files for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing class files for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def import_class_files_for_all_services(self):
        """Import class files for all services"""
        logger.info("Importing class files for all services")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            for idx, service in enumerate(services, 1):
                logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                
                success = self.import_class_files_for_service(service.service_name, service.environment)
                if not success:
                    logger.error(f"Failed to import class files for service: {service.service_name}")
                
                # Show progress
                progress = (idx / total_services) * 100
                logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("Class files import completed for all services")
            
        except Exception as e:
            logger.error(f"Error importing class files for all services: {e}")
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Import class file information to database')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Import class files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Import class files for all services')
    
    args = parser.parse_args()
    
    importer = ClassFileImporter(args.database_url)
    
    try:
        if args.all_services:
            importer.import_class_files_for_all_services()
        elif args.service_name:
            importer.import_class_files_for_service(args.service_name, args.environment)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("Class files import completed successfully!")
        
    except Exception as e:
        logger.error(f"Class files import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
