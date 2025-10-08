#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java Source Files Import Script
Import Java source files from decompiled directories to database
"""

import os
import sys
import argparse
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, JarFile, ClassFile, JavaSourceFile, JavaSourceInJarFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JavaSourceImporter:
    """Java source file importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def extract_class_info_from_path(self, file_path, base_dir, is_jar_source):
        """Extract class information from file path"""
        try:
            # Get relative path from base directory
            rel_path = os.path.relpath(file_path, base_dir)
            path_parts = rel_path.split(os.sep)
            
            if len(path_parts) < 3:
                return None
            
            if is_jar_source:
                # Format: jar_name/timestamp-service@ip/com/package/ClassName.java
                jar_name = path_parts[0]
                timestamp_dir = path_parts[1]
                java_path_parts = path_parts[2:]
            else:
                # Format: class_name/timestamp-service@ip/com/package/ClassName.java
                jar_name = None
                timestamp_dir = path_parts[1]
                java_path_parts = path_parts[2:]
            
            # Extract service name from timestamp directory
            # Format: 20250101-service_name@ip_address
            timestamp_parts = timestamp_dir.split('-')
            if len(timestamp_parts) < 2:
                return None
            
            service_ip_part = timestamp_parts[1]  # service_name@ip_address
            if '@' in service_ip_part:
                service_name = service_ip_part.split('@')[0]
            else:
                service_name = service_ip_part
            
            # Extract class full name from Java path
            if not java_path_parts or not java_path_parts[-1].endswith('.java'):
                return None
            
            # Remove .java extension
            java_path_parts[-1] = java_path_parts[-1][:-5]
            
            # Convert path to class name
            class_full_name = '.'.join(java_path_parts)
            
            return {
                'service_name': service_name,
                'jar_name': jar_name,
                'class_full_name': class_full_name
            }
            
        except Exception as e:
            logger.error(f"Error extracting class info from path {file_path}: {e}")
            return None
    
    def import_java_sources_from_jar_decompile(self, service_name, environment='production'):
        """Import Java source files from JAR decompiled directory"""
        logger.info(f"Importing Java source files from JAR decompiled directory for service: {service_name} ({environment})")
        
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
            
            jar_decompile_dir = service.jar_decompile_output_dir
            
            if not os.path.exists(jar_decompile_dir):
                logger.warning(f"JAR decompile directory not found: {jar_decompile_dir}")
                return True
            
            # Get JAR files for this service
            jar_files = {jf.jar_name: jf for jf in db.query(JarFile).filter(JarFile.service_id == service.id).all()}
            
            imported_count = 0
            updated_count = 0
            
            # Walk through decompiled directory
            for root, dirs, files in os.walk(jar_decompile_dir):
                # Skip _jar directories
                if '_jar' in root:
                    continue
                
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Extract class information from path
                            class_info = self.extract_class_info_from_path(file_path, jar_decompile_dir, True)
                            if not class_info:
                                continue
                            
                            # Verify service name matches
                            if class_info['service_name'] != service_name:
                                continue
                            
                            class_full_name = class_info['class_full_name']
                            jar_name = class_info['jar_name']
                            
                            # Find corresponding JAR file by jar_name and service
                            # jar_name from path doesn't include .jar extension, but database jar_name does
                            jar_file = None
                            for jf in jar_files.values():
                                # Compare without .jar extension
                                db_jar_name_without_ext = jf.jar_name.replace('.jar', '')
                                if db_jar_name_without_ext == jar_name:
                                    jar_file = jf
                                    break
                            
                            if not jar_file:
                                logger.warning(f"JAR file not found for class {class_full_name}: {jar_name}")
                                continue
                            
                            # Read file content
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                            
                            # Calculate file properties
                            file_size = os.path.getsize(file_path)
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            
                            # Get file modification time
                            mtime = os.path.getmtime(file_path)
                            last_modified = datetime.fromtimestamp(mtime)
                            
                            # Check if Java source file already exists
                            existing_source = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if existing_source:
                                # Update existing source file
                                existing_source.file_content = file_content
                                existing_source.file_size = file_size
                                existing_source.last_modified = last_modified
                                existing_source.file_hash = file_hash
                                existing_source.line_count = line_count
                                updated_count += 1
                                logger.debug(f"Updated Java source: {class_full_name}")
                            else:
                                # Create new source file
                                java_source = JavaSourceFile(
                                    class_full_name=class_full_name,
                                    file_path=file_path,
                                    file_content=file_content,
                                    file_size=file_size,
                                    last_modified=last_modified,
                                    file_hash=file_hash,
                                    line_count=line_count
                                )
                                db.add(java_source)
                                imported_count += 1
                                logger.debug(f"Imported Java source: {class_full_name}")
                            
                            db.commit()
                            
                            # Create or update JAR source mapping
                            java_source_file = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if java_source_file:
                                existing_mapping = db.query(JavaSourceInJarFile).filter(
                                    JavaSourceInJarFile.jar_file_id == jar_file.id,
                                    JavaSourceInJarFile.java_source_file_id == java_source_file.id
                                ).first()
                                
                                if not existing_mapping:
                                    mapping = JavaSourceInJarFile(
                                        jar_file_id=jar_file.id,
                                        java_source_file_id=java_source_file.id
                                    )
                                    db.add(mapping)
                                    db.commit()
                        
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java source file already exists: {class_full_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java source file {file_path}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new Java source files, updated {updated_count} existing files from JAR decompile for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing Java source files from JAR decompile for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def import_java_sources_from_class_decompile(self, service_name, environment='production'):
        """Import Java source files from class decompiled directory"""
        logger.info(f"Importing Java source files from class decompiled directory for service: {service_name} ({environment})")
        
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
            
            class_decompile_dir = service.class_decompile_output_dir
            
            if not os.path.exists(class_decompile_dir):
                logger.warning(f"Class decompile directory not found: {class_decompile_dir}")
                return True
            
            # Get class files for this service
            class_files = {cf.class_full_name: cf for cf in db.query(ClassFile).filter(ClassFile.service_id == service.id).all()}
            
            imported_count = 0
            updated_count = 0
            
            # Walk through decompiled directory
            for root, dirs, files in os.walk(class_decompile_dir):
                # Skip _class directories
                if '_class' in root:
                    continue
                
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Extract class information from path
                            class_info = self.extract_class_info_from_path(file_path, class_decompile_dir, False)
                            if not class_info:
                                continue
                            
                            # Verify service name matches
                            if class_info['service_name'] != service_name:
                                continue
                            
                            class_full_name = class_info['class_full_name']
                            
                            # Find corresponding class file
                            class_file = class_files.get(class_full_name)
                            if not class_file:
                                logger.warning(f"Class file not found for class: {class_full_name}")
                                continue
                            
                            # Read file content
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                            
                            # Calculate file properties
                            file_size = os.path.getsize(file_path)
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            
                            # Get file modification time
                            mtime = os.path.getmtime(file_path)
                            last_modified = datetime.fromtimestamp(mtime)
                            
                            # Check if Java source file already exists
                            existing_source = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if existing_source:
                                # Update existing source file
                                existing_source.file_content = file_content
                                existing_source.file_size = file_size
                                existing_source.last_modified = last_modified
                                existing_source.file_hash = file_hash
                                existing_source.line_count = line_count
                                updated_count += 1
                                logger.debug(f"Updated Java source: {class_full_name}")
                            else:
                                # Create new source file
                                java_source = JavaSourceFile(
                                    class_full_name=class_full_name,
                                    file_path=file_path,
                                    file_content=file_content,
                                    file_size=file_size,
                                    last_modified=last_modified,
                                    file_hash=file_hash,
                                    line_count=line_count
                                )
                                db.add(java_source)
                                imported_count += 1
                                logger.debug(f"Imported Java source: {class_full_name}")
                            
                            db.commit()
                            
                            # Update class file with source file reference
                            java_source_file = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if java_source_file:
                                class_file.java_source_file_id = java_source_file.id
                                db.commit()
                        
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java source file already exists: {class_full_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java source file {file_path}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new Java source files, updated {updated_count} existing files from class decompile for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing Java source files from class decompile for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def import_java_sources_for_service(self, service_name, environment='production'):
        """Import Java source files for a specific service"""
        logger.info(f"Importing Java source files for service: {service_name} ({environment})")
        
        # Import from JAR decompile
        jar_success = self.import_java_sources_from_jar_decompile(service_name, environment)
        
        # Import from class decompile
        class_success = self.import_java_sources_from_class_decompile(service_name, environment)
        
        return jar_success and class_success
    
    def import_java_sources_for_all_services(self):
        """Import Java source files for all services"""
        logger.info("Importing Java source files for all services")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            for idx, service in enumerate(services, 1):
                logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                
                success = self.import_java_sources_for_service(service.service_name, service.environment)
                if not success:
                    logger.error(f"Failed to import Java source files for service: {service.service_name}")
                
                # Show progress
                progress = (idx / total_services) * 100
                logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("Java source files import completed for all services")
            
        except Exception as e:
            logger.error(f"Error importing Java source files for all services: {e}")
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Import Java source files to database')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Import Java source files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Import Java source files for all services')
    
    args = parser.parse_args()
    
    importer = JavaSourceImporter(args.database_url)
    
    try:
        if args.all_services:
            importer.import_java_sources_for_all_services()
        elif args.service_name:
            importer.import_java_sources_for_service(args.service_name, args.environment)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("Java source files import completed successfully!")
        
    except Exception as e:
        logger.error(f"Java source files import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
