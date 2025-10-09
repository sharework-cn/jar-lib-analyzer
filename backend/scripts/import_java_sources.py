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
import platform
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, JarFile, ClassFile, JavaSourceFile, JavaSourceFileVersion, JavaSourceInJarFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JavaSourceFilter:
    """Filter for Java source files import"""
    
    def __init__(self, db, service_name=None, jar_name=None, class_name=None, all_services=False):
        self.db = db
        self.service_name = service_name
        self.jar_name = jar_name
        self.class_name = class_name
        self.all_services = all_services
        
        # Initialize filter results
        self.scan_directories = []
        self.target_files = []
        self.statistics = {
            'total_files': 0,
            'jar_files': 0,
            'class_files': 0,
            'services': set(),
            'jars': set()
        }
        
        # Build filter
        self._build_filter()
    
    def _build_filter(self):
        """Build the filter based on parameters"""
        # Step 1: Get scan directories
        self._get_scan_directories()
        
        # Step 2: Scan and filter files
        self._scan_and_filter_files()
    
    def _get_scan_directories(self):
        """Get directories to scan based on service filter"""
        if self.all_services:
            # Get all services and check if they have same directories
            services = self.db.query(Service).all()
            if not services:
                logger.warning("No services found in database")
                return
            
            # Check directory consistency
            jar_dirs = set()
            class_dirs = set()
            
            for service in services:
                if service.jar_decompile_output_dir:
                    jar_dirs.add(service.jar_decompile_output_dir)
                if service.class_decompile_output_dir:
                    class_dirs.add(service.class_decompile_output_dir)
            
            if len(jar_dirs) != 1 or len(class_dirs) != 1:
                raise ValueError("All services must have the same jar_decompile_output_dir and class_decompile_output_dir for --all-services mode")
            
            jar_dir = list(jar_dirs)[0]
            class_dir = list(class_dirs)[0]
            
            self.scan_directories = [
                {'path': jar_dir, 'type': 'jar', 'services': services},
                {'path': class_dir, 'type': 'class', 'services': services}
            ]
            
            logger.info(f"All-services mode: JAR dir={jar_dir}, Class dir={class_dir}")
        else:
            # Get specific service
            if not self.service_name:
                raise ValueError("Must specify --service-name when not using --all-services")
            
            service = self.db.query(Service).filter(Service.service_name == self.service_name).first()
            if not service:
                raise ValueError(f"Service not found: {self.service_name}")
            
            self.scan_directories = []
            if service.jar_decompile_output_dir:
                self.scan_directories.append({
                    'path': service.jar_decompile_output_dir,
                    'type': 'jar',
                    'services': [service]
                })
            if service.class_decompile_output_dir:
                self.scan_directories.append({
                    'path': service.class_decompile_output_dir,
                    'type': 'class',
                    'services': [service]
                })
            
            logger.info(f"Service {self.service_name}: JAR dir={service.jar_decompile_output_dir}, Class dir={service.class_decompile_output_dir}")
    
    def _scan_and_filter_files(self):
        """Scan directories and filter files based on criteria"""
        for scan_dir in self.scan_directories:
            directory_path = scan_dir['path']
            directory_type = scan_dir['type']
            services = scan_dir['services']
            
            if not os.path.exists(directory_path):
                logger.warning(f"Directory not found: {directory_path}")
                continue
            
            # Walk through directory
            for root, dirs, files in os.walk(directory_path):
                # Skip special directories
                if f'_{directory_type}' in root:
                    continue
                
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        
                        # Parse file info
                        file_info = self._parse_file_info(file_path, directory_path, directory_type)
                        if not file_info:
                            continue
                        
                        # Apply filters
                        if self._should_include_file(file_info, directory_type):
                            self.target_files.append({
                                'file_path': file_path,
                                'directory_type': directory_type,
                                'file_info': file_info
                            })
                            
                            # Update statistics
                            self.statistics['total_files'] += 1
                            self.statistics['services'].add(file_info['service_name'])
                            
                            if directory_type == 'jar':
                                self.statistics['jar_files'] += 1
                                self.statistics['jars'].add(file_info['jar_name'])
                            else:
                                self.statistics['class_files'] += 1
    
    def _parse_file_info(self, file_path, base_dir, directory_type):
        """Parse file information from path"""
        try:
            # Get relative path from base directory
            rel_path = os.path.relpath(file_path, base_dir)
            path_parts = rel_path.split(os.sep)
            
            if len(path_parts) < 3:
                return None
            
            if directory_type == 'jar':
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
                'class_full_name': class_full_name,
                'timestamp_dir': timestamp_dir
            }
            
        except Exception as e:
            logger.error(f"Error parsing file info from path {file_path}: {e}")
            return None
    
    def _should_include_file(self, file_info, directory_type):
        """Check if file should be included based on filters"""
        # Service-level filtering
        if not self.all_services:
            if file_info['service_name'] != self.service_name:
                return False
        
        # File-level filtering
        if directory_type == 'jar':
            # JAR file filtering
            if self.jar_name:
                jar_name_without_ext = self.jar_name.replace('.jar', '')
                if file_info['jar_name'] != jar_name_without_ext:
                    return False
            if self.class_name:
                # If class_name is specified but we're in jar directory, skip
                return False
        else:
            # Class file filtering
            if self.class_name:
                if file_info['class_full_name'] != self.class_name:
                    return False
            if self.jar_name:
                # If jar_name is specified but we're in class directory, skip
                return False
        
        return True
    
    def get_statistics(self):
        """Get filter statistics"""
        return {
            'total_files': self.statistics['total_files'],
            'jar_files': self.statistics['jar_files'],
            'class_files': self.statistics['class_files'],
            'services_count': len(self.statistics['services']),
            'jars_count': len(self.statistics['jars']),
            'services': sorted(list(self.statistics['services'])),
            'jars': sorted(list(self.statistics['jars']))
        }
    
    def print_statistics(self):
        """Print filter statistics"""
        stats = self.get_statistics()
        logger.info("=== Import Filter Statistics ===")
        logger.info(f"Total files to import: {stats['total_files']}")
        logger.info(f"JAR files: {stats['jar_files']}")
        logger.info(f"Class files: {stats['class_files']}")
        logger.info(f"Services: {stats['services_count']} ({', '.join(stats['services'])})")
        logger.info(f"JARs: {stats['jars_count']} ({', '.join(stats['jars'])})")
        logger.info("================================")
    
    def get_target_files(self):
        """Get list of target files to import"""
        return self.target_files

class JavaSourceImporter:
    """Java source file importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.is_windows = platform.system().lower() == 'windows'
    
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def create_filter(self, service_name=None, jar_name=None, class_name=None, all_services=False):
        """Create a filter for Java source import"""
        return JavaSourceFilter(
            self.get_db_session(), 
            service_name=service_name,
            jar_name=jar_name, 
            class_name=class_name,
            all_services=all_services
        )
    
    def import_java_sources_with_filter(self, filter_obj, dry_run=False):
        """Import Java source files using filter"""
        if dry_run:
            logger.info("=== DRY RUN MODE ===")
            filter_obj.print_statistics()
            return True
        
        logger.info("=== IMPORT MODE ===")
        filter_obj.print_statistics()
        
        target_files = filter_obj.get_target_files()
        total_files = len(target_files)
        
        if total_files == 0:
            logger.warning("No files to import")
            return True
        
        logger.info(f"Starting import of {total_files} files...")
        
        imported_count = 0
        updated_count = 0
        
        # Process files with progress tracking
        for idx, file_info in enumerate(target_files, 1):
            file_path = file_info['file_path']
            directory_type = file_info['directory_type']
            file_metadata = file_info['file_info']
            
            progress = (idx / total_files) * 100
            logger.info(f"Processing file [{idx}/{total_files}] ({progress:.1f}%): {os.path.basename(file_path)}")
            
            try:
                success = self._import_single_file(file_path, file_metadata, directory_type)
                if success:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error importing file {file_path}: {e}")
        
        logger.info(f"Import completed: {updated_count} files processed")
        return True
    
    def _import_single_file(self, file_path, file_metadata, directory_type):
        """Import a single Java source file"""
        db = self.get_db_session()
        
        try:
            # Use long path prefix for Windows compatibility
            long_path = self.get_long_path_prefix(file_path)
            
            # Read file content
            try:
                with open(long_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except (OSError, IOError) as e:
                logger.warning(f"Failed to read file with long path, trying original path: {e}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            
            # Calculate file properties
            try:
                file_size = os.path.getsize(long_path)
                mtime = os.path.getmtime(long_path)
            except (OSError, IOError):
                file_size = os.path.getsize(file_path)
                mtime = os.path.getmtime(file_path)
            
            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
            line_count = len(file_content.splitlines())
            last_modified = datetime.fromtimestamp(mtime)
            
            class_full_name = file_metadata['class_full_name']
            
            # Check if Java source file already exists
            existing_source = db.query(JavaSourceFile).filter(
                JavaSourceFile.class_full_name == class_full_name
            ).first()
            
            if not existing_source:
                # Create new Java source file
                existing_source = JavaSourceFile(
                    class_full_name=class_full_name
                )
                db.add(existing_source)
                db.flush()  # Get the ID
            
            # Create new version for this source file
            # Normalize file path to use Linux-style forward slashes
            normalized_file_path = file_path.replace('\\', '/')
            java_source_version = JavaSourceFileVersion(
                java_source_file_id=existing_source.id,
                file_path=normalized_file_path,
                file_content=file_content,
                file_size=file_size,
                last_modified=last_modified,
                file_hash=file_hash,
                line_count=line_count
            )
            db.add(java_source_version)
            db.flush()  # Get the ID
            
            # Create mappings based on file type
            if directory_type == 'jar':
                self._create_jar_mapping(file_metadata, java_source_version, db)
            else:
                self._create_class_mapping(file_metadata, java_source_version, db)
            
            db.commit()
            logger.debug(f"Imported Java source version: {class_full_name}")
            return True
            
        except IntegrityError:
            db.rollback()
            logger.warning(f"Java source file version already exists: {class_full_name}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing Java source file {file_path}: {e}")
            return False
        finally:
            db.close()
    
    def _create_jar_mapping(self, file_metadata, java_source_version, db):
        """Create JAR file mapping"""
        service_name = file_metadata['service_name']
        jar_name = file_metadata['jar_name']
        
        # Find service
        service = db.query(Service).filter(Service.service_name == service_name).first()
        if not service:
            logger.warning(f"Service not found: {service_name}")
            return
        
        # Find JAR file
        jar_file = None
        for jf in db.query(JarFile).filter(JarFile.service_id == service.id).all():
            db_jar_name_without_ext = jf.jar_name.replace('.jar', '')
            if db_jar_name_without_ext == jar_name:
                jar_file = jf
                break
        
        if not jar_file:
            logger.warning(f"JAR file not found for class {file_metadata['class_full_name']}: {jar_name}")
            return
        
        # Create mapping
        existing_mapping = db.query(JavaSourceInJarFile).filter(
            JavaSourceInJarFile.jar_file_id == jar_file.id,
            JavaSourceInJarFile.java_source_file_version_id == java_source_version.id
        ).first()
        
        if not existing_mapping:
            mapping = JavaSourceInJarFile(
                jar_file_id=jar_file.id,
                java_source_file_version_id=java_source_version.id
            )
            db.add(mapping)
    
    def _create_class_mapping(self, file_metadata, java_source_version, db):
        """Create class file mapping"""
        service_name = file_metadata['service_name']
        class_full_name = file_metadata['class_full_name']
        
        # Find service
        service = db.query(Service).filter(Service.service_name == service_name).first()
        if not service:
            logger.warning(f"Service not found: {service_name}")
            return
        
        # Find class file
        class_file = db.query(ClassFile).filter(
            ClassFile.service_id == service.id,
            ClassFile.class_full_name == class_full_name
        ).first()
        
        if not class_file:
            logger.warning(f"Class file not found for class: {class_full_name}")
            return
        
        # Update class file with source file version reference
        class_file.java_source_file_version_id = java_source_version.id
    
    def get_long_path_prefix(self, path_str):
        """Convert normal path to UNC format path that supports long paths."""
        if not self.is_windows:
            return path_str
            
        # Ensure it's an absolute path
        abs_path = os.path.abspath(path_str)
        # Check if it's already UNC format or network path
        if abs_path.startswith('\\\\'):
            # Network path or UNC path
            if abs_path.startswith('\\\\?\\'):
                return abs_path
            else:
                # For network paths, use \\?\UNC\ prefix
                unc_path = abs_path.replace('\\\\', '\\', 1)  # Ensure only two backslashes at start
                return f"\\\\?\\UNC\\{unc_path[2:]}"  # Remove leading \\ and add \\?\UNC\
        else:
            # Local path, directly add \\?\ prefix
            return f"\\\\?\\{abs_path}"
    
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
    
    def import_java_sources_from_jar_decompile(self, service_name, environment='production', jar_name=None):
        """Import Java source files from JAR decompiled directory"""
        logger.info(f"Importing Java source files from JAR decompiled directory for service: {service_name} ({environment})")
        if jar_name:
            logger.info(f"Using jar-name parameter: {jar_name}")
        
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
            
            # Determine base directory for walking
            if jar_name:
                # Remove .jar extension if present
                jar_dir_name = jar_name.replace('.jar', '')
                base_walk_dir = os.path.join(jar_decompile_dir, jar_dir_name)
                if not os.path.exists(base_walk_dir):
                    logger.warning(f"JAR directory not found: {base_walk_dir}")
                    return True
            else:
                base_walk_dir = jar_decompile_dir
            
            # First, count total directories to process for progress tracking
            total_dirs = 0
            for root, dirs, files in os.walk(base_walk_dir):
                if '_jar' in root:
                    continue
                if any(f.endswith('.java') for f in files):
                    total_dirs += 1
            
            logger.info(f"Found {total_dirs} directories with Java files in JAR decompile directory")
            
            # Walk through decompiled directory with progress tracking
            processed_dirs = 0
            for root, dirs, files in os.walk(base_walk_dir):
                # Skip _jar directories
                if '_jar' in root:
                    continue
                
                # Skip directories without Java files
                if not any(f.endswith('.java') for f in files):
                    continue
                
                processed_dirs += 1
                progress = (processed_dirs / total_dirs) * 100 if total_dirs > 0 else 0
                logger.info(f"Processing JAR directory [{processed_dirs}/{total_dirs}] ({progress:.1f}%): {os.path.basename(root)}")
                
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Use long path prefix for Windows compatibility
                            long_path = self.get_long_path_prefix(file_path)
                            
                            # Extract class information from path
                            class_info = self.extract_class_info_from_path(file_path, jar_decompile_dir, True)
                            if not class_info:
                                continue
                            
                            # Verify service name matches
                            if class_info['service_name'] != service_name:
                                continue
                            
                            class_full_name = class_info['class_full_name']
                            path_jar_name = class_info['jar_name']
                            
                            # If jar_name parameter is specified, use it; otherwise use path_jar_name
                            target_jar_name = jar_name.replace('.jar', '') if jar_name else path_jar_name
                            
                            # Find corresponding JAR file by jar_name and service
                            jar_file = None
                            for jf in jar_files.values():
                                # Compare without .jar extension
                                db_jar_name_without_ext = jf.jar_name.replace('.jar', '')
                                if db_jar_name_without_ext == target_jar_name:
                                    jar_file = jf
                                    break
                            
                            if not jar_file:
                                logger.warning(f"JAR file not found for class {class_full_name}: {target_jar_name}")
                                continue
                            
                            # Read file content using long path
                            try:
                                with open(long_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    file_content = f.read()
                            except (OSError, IOError) as e:
                                logger.warning(f"Failed to read file with long path, trying original path: {e}")
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    file_content = f.read()
                            
                            # Calculate file properties
                            try:
                                file_size = os.path.getsize(long_path)
                                mtime = os.path.getmtime(long_path)
                            except (OSError, IOError):
                                file_size = os.path.getsize(file_path)
                                mtime = os.path.getmtime(file_path)
                            
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            last_modified = datetime.fromtimestamp(mtime)
                            
                            # Check if Java source file already exists
                            existing_source = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if not existing_source:
                                # Create new Java source file
                                existing_source = JavaSourceFile(
                                    class_full_name=class_full_name
                                )
                                db.add(existing_source)
                                db.flush()  # Get the ID
                                imported_count += 1
                                logger.debug(f"Created Java source file: {class_full_name}")
                            
                            # Create new version for this source file
                            # Normalize file path to use Linux-style forward slashes
                            normalized_file_path = file_path.replace('\\', '/')
                            java_source_version = JavaSourceFileVersion(
                                java_source_file_id=existing_source.id,
                                file_path=normalized_file_path,
                                file_content=file_content,
                                file_size=file_size,
                                last_modified=last_modified,
                                file_hash=file_hash,
                                line_count=line_count
                            )
                            db.add(java_source_version)
                            db.flush()  # Get the ID
                            
                            # Create or update JAR source mapping
                            existing_mapping = db.query(JavaSourceInJarFile).filter(
                                JavaSourceInJarFile.jar_file_id == jar_file.id,
                                JavaSourceInJarFile.java_source_file_version_id == java_source_version.id
                            ).first()
                            
                            if not existing_mapping:
                                mapping = JavaSourceInJarFile(
                                    jar_file_id=jar_file.id,
                                    java_source_file_version_id=java_source_version.id
                                )
                                db.add(mapping)
                            
                            db.commit()
                            updated_count += 1
                            logger.debug(f"Imported Java source version: {class_full_name}")
                        
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java source file version already exists: {class_full_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java source file {file_path}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new Java source files, created {updated_count} versions from JAR decompile for service: {service_name}")
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
            
            # First, count total directories to process for progress tracking
            total_dirs = 0
            for root, dirs, files in os.walk(class_decompile_dir):
                if '_class' in root:
                    continue
                if any(f.endswith('.java') for f in files):
                    total_dirs += 1
            
            logger.info(f"Found {total_dirs} directories with Java files in class decompile directory")
            
            # Walk through decompiled directory with progress tracking
            processed_dirs = 0
            for root, dirs, files in os.walk(class_decompile_dir):
                # Skip _class directories
                if '_class' in root:
                    continue
                
                # Skip directories without Java files
                if not any(f.endswith('.java') for f in files):
                    continue
                
                processed_dirs += 1
                progress = (processed_dirs / total_dirs) * 100 if total_dirs > 0 else 0
                logger.info(f"Processing class directory [{processed_dirs}/{total_dirs}] ({progress:.1f}%): {os.path.basename(root)}")
                
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Use long path prefix for Windows compatibility
                            long_path = self.get_long_path_prefix(file_path)
                            
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
                            
                            # Read file content using long path
                            try:
                                with open(long_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    file_content = f.read()
                            except (OSError, IOError) as e:
                                logger.warning(f"Failed to read file with long path, trying original path: {e}")
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    file_content = f.read()
                            
                            # Calculate file properties
                            try:
                                file_size = os.path.getsize(long_path)
                                mtime = os.path.getmtime(long_path)
                            except (OSError, IOError):
                                file_size = os.path.getsize(file_path)
                                mtime = os.path.getmtime(file_path)
                            
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            last_modified = datetime.fromtimestamp(mtime)
                            
                            # Check if Java source file already exists
                            existing_source = db.query(JavaSourceFile).filter(
                                JavaSourceFile.class_full_name == class_full_name
                            ).first()
                            
                            if not existing_source:
                                # Create new Java source file
                                existing_source = JavaSourceFile(
                                    class_full_name=class_full_name
                                )
                                db.add(existing_source)
                                db.flush()  # Get the ID
                                imported_count += 1
                                logger.debug(f"Created Java source file: {class_full_name}")
                            
                            # Create new version for this source file
                            # Normalize file path to use Linux-style forward slashes
                            normalized_file_path = file_path.replace('\\', '/')
                            java_source_version = JavaSourceFileVersion(
                                java_source_file_id=existing_source.id,
                                file_path=normalized_file_path,
                                file_content=file_content,
                                file_size=file_size,
                                last_modified=last_modified,
                                file_hash=file_hash,
                                line_count=line_count
                            )
                            db.add(java_source_version)
                            db.flush()  # Get the ID
                            
                            # Update class file with source file version reference
                            class_file.java_source_file_version_id = java_source_version.id
                            
                            db.commit()
                            updated_count += 1
                            logger.debug(f"Imported Java source version: {class_full_name}")
                        
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java source file version already exists: {class_full_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java source file {file_path}: {e}")
            
            logger.info(f"Successfully imported {imported_count} new Java source files, created {updated_count} versions from class decompile for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing Java source files from class decompile for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def import_java_sources_for_service(self, service_name, environment='production', jar_name=None):
        """Import Java source files for a specific service"""
        logger.info(f"Importing Java source files for service: {service_name} ({environment})")
        
        # Import from JAR decompile
        jar_success = self.import_java_sources_from_jar_decompile(service_name, environment, jar_name)
        
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
            
            if total_services == 0:
                logger.warning("No services found in database")
                return
            
            # Check if all services have the same jar_decompile_output_dir and class_decompile_output_dir
            jar_dirs = set()
            class_dirs = set()
            
            for service in services:
                if service.jar_decompile_output_dir:
                    jar_dirs.add(service.jar_decompile_output_dir)
                if service.class_decompile_output_dir:
                    class_dirs.add(service.class_decompile_output_dir)
            
            logger.info(f"Found {len(jar_dirs)} unique JAR decompile directories")
            logger.info(f"Found {len(class_dirs)} unique class decompile directories")
            
            # If all services have the same directories, use optimized import
            if len(jar_dirs) == 1 and len(class_dirs) == 1:
                jar_dir = list(jar_dirs)[0]
                class_dir = list(class_dirs)[0]
                
                logger.info(f"All services use the same directories:")
                logger.info(f"  JAR decompile dir: {jar_dir}")
                logger.info(f"  Class decompile dir: {class_dir}")
                
                # Import from unified directories
                self._import_from_unified_directories(jar_dir, class_dir, services, db)
            else:
                logger.info("Services have different directories, processing individually")
                
                # Process each service individually
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
    
    def _import_from_unified_directories(self, jar_dir, class_dir, services, db):
        """Import from unified directories when all services use the same paths"""
        logger.info("Importing from unified directories")
        
        # Get all JAR files for all services
        service_ids = [s.id for s in services]
        jar_files = {jf.jar_name: jf for jf in db.query(JarFile).filter(JarFile.service_id.in_(service_ids)).all()}
        class_files = {cf.class_full_name: cf for cf in db.query(ClassFile).filter(ClassFile.service_id.in_(service_ids)).all()}
        
        imported_count = 0
        updated_count = 0
        
        # Import from JAR decompile directory
        if os.path.exists(jar_dir):
            logger.info(f"Processing JAR decompile directory: {jar_dir}")
            jar_imported, jar_updated = self._process_unified_jar_directory(jar_dir, jar_files, services, db)
            imported_count += jar_imported
            updated_count += jar_updated
        else:
            logger.warning(f"JAR decompile directory not found: {jar_dir}")
        
        # Import from class decompile directory
        if os.path.exists(class_dir):
            logger.info(f"Processing class decompile directory: {class_dir}")
            class_imported, class_updated = self._process_unified_class_directory(class_dir, class_files, services, db)
            imported_count += class_imported
            updated_count += class_updated
        else:
            logger.warning(f"Class decompile directory not found: {class_dir}")
        
        logger.info(f"Unified import completed: {imported_count} new files, {updated_count} versions created")
    
    def _process_unified_jar_directory(self, jar_dir, jar_files, services, db):
        """Process unified JAR decompile directory - import all files without service name filtering"""
        imported_count = 0
        updated_count = 0
        
        # First, count total directories to process for progress tracking
        total_dirs = 0
        for root, dirs, files in os.walk(jar_dir):
            if '_jar' in root:
                continue
            if any(f.endswith('.java') for f in files):
                total_dirs += 1
        
        logger.info(f"Found {total_dirs} directories with Java files in JAR decompile directory")
        
        # Process directories with progress tracking
        processed_dirs = 0
        for root, dirs, files in os.walk(jar_dir):
            # Skip _jar directories
            if '_jar' in root:
                continue
            
            # Skip directories without Java files
            if not any(f.endswith('.java') for f in files):
                continue
            
            processed_dirs += 1
            progress = (processed_dirs / total_dirs) * 100 if total_dirs > 0 else 0
            logger.info(f"Processing JAR directory [{processed_dirs}/{total_dirs}] ({progress:.1f}%): {os.path.basename(root)}")
            
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Use long path prefix for Windows compatibility
                        long_path = self.get_long_path_prefix(file_path)
                        
                        # Extract class information from path
                        class_info = self.extract_class_info_from_path(file_path, jar_dir, True)
                        if not class_info:
                            continue
                        
                        service_name = class_info['service_name']
                        class_full_name = class_info['class_full_name']
                        jar_name = class_info['jar_name']
                        
                        # Find corresponding service (but don't skip if not found in all-services mode)
                        service = next((s for s in services if s.service_name == service_name), None)
                        
                        # Find corresponding JAR file across all services
                        jar_file = None
                        for jf in jar_files.values():
                            db_jar_name_without_ext = jf.jar_name.replace('.jar', '')
                            if db_jar_name_without_ext == jar_name:
                                jar_file = jf
                                break
                        
                        if not jar_file:
                            logger.warning(f"JAR file not found for class {class_full_name}: {jar_name}")
                            continue
                        
                        # Process the file (same logic as individual service import)
                        success = self._process_java_file(file_path, long_path, class_full_name, jar_file, db)
                        if success:
                            updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing Java file {file_path}: {e}")
        
        return imported_count, updated_count
    
    def _process_unified_class_directory(self, class_dir, class_files, services, db):
        """Process unified class decompile directory - import all files without service name filtering"""
        imported_count = 0
        updated_count = 0
        
        # First, count total directories to process for progress tracking
        total_dirs = 0
        for root, dirs, files in os.walk(class_dir):
            if '_class' in root:
                continue
            if any(f.endswith('.java') for f in files):
                total_dirs += 1
        
        logger.info(f"Found {total_dirs} directories with Java files in class decompile directory")
        
        # Process directories with progress tracking
        processed_dirs = 0
        for root, dirs, files in os.walk(class_dir):
            # Skip _class directories
            if '_class' in root:
                continue
            
            # Skip directories without Java files
            if not any(f.endswith('.java') for f in files):
                continue
            
            processed_dirs += 1
            progress = (processed_dirs / total_dirs) * 100 if total_dirs > 0 else 0
            logger.info(f"Processing class directory [{processed_dirs}/{total_dirs}] ({progress:.1f}%): {os.path.basename(root)}")
            
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Use long path prefix for Windows compatibility
                        long_path = self.get_long_path_prefix(file_path)
                        
                        # Extract class information from path
                        class_info = self.extract_class_info_from_path(file_path, class_dir, False)
                        if not class_info:
                            continue
                        
                        service_name = class_info['service_name']
                        class_full_name = class_info['class_full_name']
                        
                        # Find corresponding service (but don't skip if not found in all-services mode)
                        service = next((s for s in services if s.service_name == service_name), None)
                        
                        # Find corresponding class file across all services
                        class_file = None
                        for cf in class_files.values():
                            if cf.class_full_name == class_full_name:
                                class_file = cf
                                break
                        
                        if not class_file:
                            logger.warning(f"Class file not found for class: {class_full_name}")
                            continue
                        
                        # Process the file (same logic as individual service import)
                        success = self._process_java_file(file_path, long_path, class_full_name, None, db, class_file)
                        if success:
                            updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing Java file {file_path}: {e}")
        
        return imported_count, updated_count
    
    def _process_java_file(self, file_path, long_path, class_full_name, jar_file, db, class_file=None):
        """Process a single Java file and create version"""
        try:
            # Read file content using long path
            try:
                with open(long_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except (OSError, IOError) as e:
                logger.warning(f"Failed to read file with long path, trying original path: {e}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            
            # Calculate file properties
            try:
                file_size = os.path.getsize(long_path)
                mtime = os.path.getmtime(long_path)
            except (OSError, IOError):
                file_size = os.path.getsize(file_path)
                mtime = os.path.getmtime(file_path)
            
            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
            line_count = len(file_content.splitlines())
            last_modified = datetime.fromtimestamp(mtime)
            
            # Check if Java source file already exists
            existing_source = db.query(JavaSourceFile).filter(
                JavaSourceFile.class_full_name == class_full_name
            ).first()
            
            if not existing_source:
                # Create new Java source file
                existing_source = JavaSourceFile(
                    class_full_name=class_full_name
                )
                db.add(existing_source)
                db.flush()  # Get the ID
            
            # Create new version for this source file
            # Normalize file path to use Linux-style forward slashes
            normalized_file_path = file_path.replace('\\', '/')
            java_source_version = JavaSourceFileVersion(
                java_source_file_id=existing_source.id,
                file_path=normalized_file_path,
                file_content=file_content,
                file_size=file_size,
                last_modified=last_modified,
                file_hash=file_hash,
                line_count=line_count
            )
            db.add(java_source_version)
            db.flush()  # Get the ID
            
            # Create mappings based on file type
            if jar_file:
                # JAR file mapping
                existing_mapping = db.query(JavaSourceInJarFile).filter(
                    JavaSourceInJarFile.jar_file_id == jar_file.id,
                    JavaSourceInJarFile.java_source_file_version_id == java_source_version.id
                ).first()
                
                if not existing_mapping:
                    mapping = JavaSourceInJarFile(
                        jar_file_id=jar_file.id,
                        java_source_file_version_id=java_source_version.id
                    )
                    db.add(mapping)
            
            if class_file:
                # Class file mapping
                class_file.java_source_file_version_id = java_source_version.id
            
            db.commit()
            logger.debug(f"Imported Java source version: {class_full_name}")
            return True
            
        except IntegrityError:
            db.rollback()
            logger.warning(f"Java source file version already exists: {class_full_name}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing Java source file {file_path}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Import Java source files to database')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Import Java source files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--jar-name',
                       help='JAR name parameter - when specified, only processes files from this specific JAR')
    parser.add_argument('--class-name',
                       help='Class name parameter - when specified, only processes files with this specific class name')
    parser.add_argument('--all-services', action='store_true',
                       help='Import Java source files for all services')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - show statistics without importing')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all_services and not args.service_name:
        logger.error("Must specify either --service-name or --all-services")
        sys.exit(1)
    
    if args.all_services and args.service_name:
        logger.error("Cannot specify both --all-services and --service-name")
        sys.exit(1)
    
    importer = JavaSourceImporter(args.database_url)
    
    try:
        # Create filter
        filter_obj = importer.create_filter(
            service_name=args.service_name,
            jar_name=args.jar_name,
            class_name=args.class_name,
            all_services=args.all_services
        )
        
        # Import using filter
        success = importer.import_java_sources_with_filter(filter_obj, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                logger.info("Dry run completed successfully!")
            else:
                logger.info("Java source files import completed successfully!")
        else:
            logger.error("Import failed")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Java source files import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
