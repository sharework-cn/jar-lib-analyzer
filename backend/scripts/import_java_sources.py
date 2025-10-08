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

class JavaSourceImporter:
    """Java source file importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.is_windows = platform.system().lower() == 'windows'
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
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
                       help='JAR name parameter - when specified, uses jar-name (without .jar extension) as the first-level subdirectory in jar decompile output directory')
    parser.add_argument('--all-services', action='store_true',
                       help='Import Java source files for all services')
    
    args = parser.parse_args()
    
    importer = JavaSourceImporter(args.database_url)
    
    try:
        if args.all_services:
            importer.import_java_sources_for_all_services()
        elif args.service_name:
            importer.import_java_sources_for_service(args.service_name, args.environment, args.jar_name)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("Java source files import completed successfully!")
        
    except Exception as e:
        logger.error(f"Java source files import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
