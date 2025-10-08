#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Import Script for Source Code Difference Analysis System
Handles CSV import and Java source file import
"""

import os
import sys
import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import argparse
import logging

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import Service, JarFile, JavaSourceFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataImporter:
    """Data importer for the source code difference analysis system"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def import_services_from_csv(self, csv_file_path, service_filter=None):
        """Import services from server_info.csv"""
        logger.info(f"Importing services from {csv_file_path}")
        
        try:
            # Try different encodings
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_file_path, encoding=encoding)
                    logger.info(f"Successfully loaded CSV using encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise Exception("Unable to read CSV file with any encoding")
            
            # Handle different column counts
            if len(df.columns) == 6:
                df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir']
                df['server_base_path'] = ''
                df['classes_path'] = ''
                df['source_path'] = ''
            elif len(df.columns) == 7:
                df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'jar_dir', 'classes_path']
                df['server_base_path'] = ''
                df['source_path'] = ''
            elif len(df.columns) == 9:
                df.columns = ['ip', 'port', 'username', 'password', 'service_name', 'server_base_path', 'jar_dir', 'classes_path', 'source_path']
            else:
                raise Exception(f"Unsupported column count: {len(df.columns)}")
            
            # Apply service filter if specified
            if service_filter:
                df = df[df['service_name'] == service_filter]
                logger.info(f"Filtered to service: {service_filter}")
            
            db = self.get_db_session()
            imported_count = 0
            
            for _, row in df.iterrows():
                try:
                    service = Service(
                        service_name=row['service_name'],
                        ip_address=row['ip'] if pd.notna(row['ip']) else None,
                        port=int(row['port']) if pd.notna(row['port']) else None,
                        username=row['username'] if pd.notna(row['username']) else None,
                        password=row['password'] if pd.notna(row['password']) else None,
                        server_base_path=row['server_base_path'] if pd.notna(row['server_base_path']) else None,
                        jar_path=row['jar_dir'] if pd.notna(row['jar_dir']) else None,
                        classes_path=row['classes_path'] if pd.notna(row['classes_path']) else None,
                        source_path=row['source_path'] if pd.notna(row['source_path']) else None
                    )
                    
                    db.add(service)
                    db.commit()
                    imported_count += 1
                    logger.info(f"Imported service: {row['service_name']}")
                    
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"Service {row['service_name']} already exists, skipping")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error importing service {row['service_name']}: {e}")
            
            db.close()
            logger.info(f"Successfully imported {imported_count} services")
            
        except Exception as e:
            logger.error(f"Error importing services: {e}")
            raise
    
    def import_jar_files_from_csv(self, csv_file_path, service_filter=None):
        """Import JAR files from analysis report CSV"""
        logger.info(f"Importing JAR files from {csv_file_path}")
        
        try:
            # Load CSV with different encodings
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_file_path, encoding=encoding)
                    logger.info(f"Successfully loaded CSV using encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise Exception("Unable to read CSV file with any encoding")
            
            db = self.get_db_session()
            
            # Get all services for mapping
            services = {s.service_name: s.id for s in db.query(Service).all()}
            
            imported_count = 0
            
            # Process each JAR file row
            for _, row in df.iterrows():
                jar_name = row['JAR_Filename']
                is_third_party = row['Third_Party_Dependency'] == 'Yes'
                
                # Process each service column
                for col in df.columns:
                    if col in ['JAR_Filename', 'Third_Party_Dependency']:
                        continue
                    
                    # Extract service name from column (format: service_name_IP_address_attribute)
                    if '_Size' in col:
                        service_key = col.replace('_Size', '')
                        service_name = self._extract_service_name_from_key(service_key)
                        
                        # Apply service filter if specified
                        if service_filter and service_name != service_filter:
                            continue
                        
                        if service_name in services and pd.notna(row[col]):
                            try:
                                # Get last modified date from the corresponding column
                                last_modified_col = col.replace('_Size', '_Last_Update_Date')
                                last_modified = None
                                if last_modified_col in df.columns and pd.notna(row[last_modified_col]):
                                    try:
                                        last_modified = pd.to_datetime(row[last_modified_col])
                                    except:
                                        pass
                                
                                jar_file = JarFile(
                                    service_id=services[service_name],
                                    jar_name=jar_name,
                                    file_size=int(row[col]) if pd.notna(row[col]) else None,
                                    last_modified=last_modified,
                                    is_third_party=is_third_party,
                                    is_latest=False  # Will be determined later
                                )
                                
                                db.add(jar_file)
                                db.commit()
                                imported_count += 1
                                logger.debug(f"Imported JAR: {jar_name} for service: {service_name}")
                                
                            except IntegrityError:
                                db.rollback()
                                logger.warning(f"JAR {jar_name} for service {service_name} already exists")
                            except Exception as e:
                                db.rollback()
                                logger.error(f"Error importing JAR {jar_name} for service {service_name}: {e}")
            
            db.close()
            logger.info(f"Successfully imported {imported_count} JAR files")
            
        except Exception as e:
            logger.error(f"Error importing JAR files: {e}")
            raise
    
    def import_java_source_files_from_jars(self, lib_decompile_dir, jar_csv_path, service_filter=None):
        """Import Java source files from JAR decompiled directory"""
        logger.info(f"Importing Java source files from JAR decompiled directory: {lib_decompile_dir}")
        
        # Load JAR analysis CSV for timestamp lookup
        jar_analysis_df = self._load_analysis_csv(jar_csv_path)
        
        db = self.get_db_session()
        
        try:
            # Get all services and JAR files for mapping
            services = {s.service_name: s.id for s in db.query(Service).all()}
            jar_files = {}
            for jf in db.query(JarFile).all():
                key = f"{jf.service_id}_{jf.jar_name}"
                jar_files[key] = jf.id
            
            imported_count = 0
            
            if os.path.exists(lib_decompile_dir):
                imported_count = self._process_jar_decompile_directory(
                    lib_decompile_dir, db, services, jar_files, jar_analysis_df, service_filter
                )
            
            logger.info(f"Successfully imported {imported_count} Java source files from JARs")
            
        finally:
            db.close()
    
    def import_java_source_files_from_classes(self, classes_decompile_dir, classes_csv_path, service_filter=None):
        """Import Java source files from class decompiled directory"""
        logger.info(f"Importing Java source files from class decompiled directory: {classes_decompile_dir}")
        
        # Load classes analysis CSV for timestamp lookup
        classes_analysis_df = self._load_analysis_csv(classes_csv_path)
        
        db = self.get_db_session()
        
        try:
            # Get all services for mapping
            services = {s.service_name: s.id for s in db.query(Service).all()}
            
            imported_count = 0
            
            if os.path.exists(classes_decompile_dir):
                imported_count = self._process_class_decompile_directory(
                    classes_decompile_dir, db, services, classes_analysis_df, service_filter
                )
            
            logger.info(f"Successfully imported {imported_count} Java source files from classes")
            
        finally:
            db.close()
    
    def _load_analysis_csv(self, csv_path):
        """Load analysis CSV file for timestamp lookup"""
        try:
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    logger.info(f"Successfully loaded analysis CSV using encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise Exception("Unable to read analysis CSV file with any encoding")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading analysis CSV {csv_path}: {e}")
            return None
    
    def _get_last_modified_from_analysis(self, class_full_name, service_name, analysis_df, file_type='jar'):
        """Get last modified timestamp from analysis CSV"""
        if analysis_df is None:
            return None
        
        try:
            # Look for the class in the analysis data
            # For JAR files, look in JAR_Filename column
            # For class files, look in JAR_Filename column (which contains class names)
            
            if file_type == 'jar':
                # For JAR decompiled files, find the JAR that contains this class
                # This is more complex as we need to match the class to its JAR
                return None  # Will use file system timestamp for now
            else:
                # For class files, look for exact match in JAR_Filename column
                matching_rows = analysis_df[analysis_df['JAR_Filename'] == f"{class_full_name}.class"]
                
                if not matching_rows.empty:
                    # Find the service-specific column for last modified date
                    for col in analysis_df.columns:
                        if col.startswith(f"{service_name}_") and col.endswith('_Last_Update_Date'):
                            last_modified_value = matching_rows.iloc[0][col]
                            if pd.notna(last_modified_value):
                                try:
                                    return pd.to_datetime(last_modified_value)
                                except:
                                    pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting last modified for {class_full_name}: {e}")
            return None
    
    def _process_jar_decompile_directory(self, decompile_dir, db, services, jar_files, analysis_df, service_filter=None):
        """Process JAR decompiled directory and import Java source files"""
        imported_count = 0
        
        for root, dirs, files in os.walk(decompile_dir):
            # Skip _jar directories
            if '_jar' in root:
                continue
            
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Extract service and class information from path
                        class_info = self._extract_class_info_from_path(file_path, decompile_dir, True)
                        if not class_info:
                            continue
                        
                        service_name = class_info['service_name']
                        class_full_name = class_info['class_full_name']
                        jar_name = class_info.get('jar_name')
                        
                        # Apply service filter if specified
                        if service_filter and service_name != service_filter:
                            continue
                        
                        if service_name not in services:
                            logger.warning(f"Service {service_name} not found for file: {file_path}")
                            continue
                        
                        service_id = services[service_name]
                        
                        # Find corresponding JAR file
                        jar_file_id = None
                        if jar_name:
                            jar_key = f"{service_id}_{jar_name}"
                            jar_file_id = jar_files.get(jar_key)
                        
                        # Get file stats and content
                        try:
                            stat = os.stat(file_path)
                            file_size = stat.st_size
                            
                            # Read file content
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                            
                            # Calculate file hash and line count
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            
                            # Get last modified time from analysis data
                            last_modified = self._get_last_modified_from_analysis(
                                class_full_name, service_name, analysis_df, 'jar'
                            )
                            
                            # If not found in analysis, use file system timestamp
                            if last_modified is None:
                                last_modified = datetime.fromtimestamp(stat.st_mtime)
                            
                            # Create Java source file record
                            java_source = JavaSourceFile(
                                service_id=service_id,
                                jar_file_id=jar_file_id,
                                class_full_name=class_full_name,
                                file_path=file_path,
                                file_content=file_content,
                                file_size=file_size,
                                last_modified=last_modified,
                                is_latest=False,  # Will be determined later
                                file_hash=file_hash,
                                line_count=line_count
                            )
                            
                            db.add(java_source)
                            db.commit()
                            imported_count += 1
                            logger.debug(f"Imported Java file from JAR: {class_full_name} from {service_name}")
                            
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java file already exists: {class_full_name} from {service_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java file {file_path}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
        
        return imported_count
    
    def _process_class_decompile_directory(self, decompile_dir, db, services, analysis_df, service_filter=None):
        """Process class decompiled directory and import Java source files"""
        imported_count = 0
        
        for root, dirs, files in os.walk(decompile_dir):
            # Skip _class directories
            if '_class' in root:
                continue
            
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Extract service and class information from path
                        class_info = self._extract_class_info_from_path(file_path, decompile_dir, False)
                        if not class_info:
                            logger.debug(f"Could not extract class info from: {file_path}")
                            continue
                        
                        service_name = class_info['service_name']
                        class_full_name = class_info['class_full_name']
                        
                        # Apply service filter if specified
                        if service_filter and service_name != service_filter:
                            logger.debug(f"Skipping {service_name} (filter: {service_filter})")
                            continue
                        
                        if service_name not in services:
                            logger.warning(f"Service {service_name} not found for file: {file_path}")
                            continue
                        
                        service_id = services[service_name]
                        
                        # Get file stats and content
                        try:
                            stat = os.stat(file_path)
                            file_size = stat.st_size
                            
                            # Read file content
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                            
                            # Calculate file hash and line count
                            file_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                            line_count = len(file_content.splitlines())
                            
                            # Get last modified time from analysis data
                            last_modified = self._get_last_modified_from_analysis(
                                class_full_name, service_name, analysis_df, 'class'
                            )
                            
                            # If not found in analysis, use file system timestamp
                            if last_modified is None:
                                last_modified = datetime.fromtimestamp(stat.st_mtime)
                            
                            # Create Java source file record
                            java_source = JavaSourceFile(
                                service_id=service_id,
                                jar_file_id=None,  # Class files don't have JAR file reference
                                class_full_name=class_full_name,
                                file_path=file_path,
                                file_content=file_content,
                                file_size=file_size,
                                last_modified=last_modified,
                                is_latest=False,  # Will be determined later
                                file_hash=file_hash,
                                line_count=line_count
                            )
                            
                            db.add(java_source)
                            db.commit()
                            imported_count += 1
                            logger.debug(f"Imported Java file from class: {class_full_name} from {service_name}")
                            
                        except IntegrityError:
                            db.rollback()
                            logger.warning(f"Java file already exists: {class_full_name} from {service_name}")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error importing Java file {file_path}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
        
        return imported_count
    
    def _extract_service_name_from_key(self, service_key):
        """Extract service name from service key (e.g., dsop_cmpp_10_176_24_135)"""
        # Remove IP address part (last 4 parts separated by underscores)
        parts = service_key.split('_')
        if len(parts) >= 5 and parts[-4].isdigit():
            # Remove last 4 parts (IP address)
            service_name = '_'.join(parts[:-4])
        else:
            service_name = service_key
        return service_name
    
    def import_java_source_files(self, lib_decompile_dir, classes_decompile_dir):
        """Import Java source files from decompiled directories"""
        logger.info("Importing Java source files from decompiled directories")
        
        db = self.get_db_session()
        
        # Get all services and JAR files for mapping
        services = {s.service_name: s.id for s in db.query(Service).all()}
        jar_files = {}
        
        for jf in db.query(JarFile).all():
            service_name = db.query(Service).filter(Service.id == jf.service_id).first().service_name
            jar_files[f"{service_name}_{jf.jar_name}"] = jf.id
        
        imported_count = 0
        
        # Import from JAR decompiled sources
        if os.path.exists(lib_decompile_dir):
            imported_count += self._import_from_directory(
                lib_decompile_dir, db, services, jar_files, is_jar_source=True
            )
        
        # Import from class decompiled sources
        if os.path.exists(classes_decompile_dir):
            imported_count += self._import_from_directory(
                classes_decompile_dir, db, services, jar_files, is_jar_source=False
            )
        
        db.close()
        logger.info(f"Successfully imported {imported_count} Java source files")
    
    def _import_from_directory(self, base_dir, db, services, jar_files, is_jar_source=True):
        """Import Java files from a specific directory"""
        imported_count = 0
        
        for root, dirs, files in os.walk(base_dir):
            # Skip _jar and _class directories
            dirs[:] = [d for d in dirs if d not in ['_jar', '_class']]
            
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Extract information from file path
                        class_info = self._extract_class_info_from_path(
                            file_path, base_dir, is_jar_source
                        )
                        
                        if not class_info:
                            continue
                        
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Calculate file properties
                        file_size = os.path.getsize(file_path)
                        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                        line_count = len(content.splitlines())
                        
                        # Get file modification time
                        mtime = os.path.getmtime(file_path)
                        last_modified = datetime.fromtimestamp(mtime)
                        
                        # Find service ID
                        service_id = services.get(class_info['service_name'])
                        if not service_id:
                            logger.warning(f"Service not found: {class_info['service_name']}")
                            continue
                        
                        # Find JAR file ID (if applicable)
                        jar_file_id = None
                        if is_jar_source and class_info['jar_name']:
                            jar_key = f"{class_info['service_name']}_{class_info['jar_name']}"
                            jar_file_id = jar_files.get(jar_key)
                        
                        # Create Java source file record
                        java_file = JavaSourceFile(
                            service_id=service_id,
                            jar_file_id=jar_file_id,
                            class_full_name=class_info['class_full_name'],
                            file_path=file_path,
                            file_content=content,
                            file_size=file_size,
                            last_modified=last_modified,
                            is_latest=False,  # Will be determined later
                            file_hash=file_hash,
                            line_count=line_count
                        )
                        
                        db.add(java_file)
                        db.commit()
                        imported_count += 1
                        
                        logger.debug(f"Imported Java file: {class_info['class_full_name']}")
                        
                    except IntegrityError:
                        db.rollback()
                        logger.warning(f"Java file already exists: {file_path}")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Error importing Java file {file_path}: {e}")
        
        return imported_count
    
    def _extract_class_info_from_path(self, file_path, base_dir, is_jar_source):
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

def main():
    parser = argparse.ArgumentParser(description='Import data for Source Code Difference Analysis System')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--services-csv', help='Path to services CSV file (server_info.csv)')
    parser.add_argument('--jar-csv', help='Path to JAR analysis CSV file')
    parser.add_argument('--classes-csv', help='Path to classes analysis CSV file')
    parser.add_argument('--lib-decompile-dir', help='Path to JAR decompiled directory')
    parser.add_argument('--classes-decompile-dir', help='Path to class decompiled directory')
    parser.add_argument('--all', action='store_true', help='Import all data')
    parser.add_argument('--service-filter', help='Only import data for specific service (e.g., dsop_cmpp)')
    parser.add_argument('--import-jars', action='store_true', help='Import JAR files and their decompiled sources')
    parser.add_argument('--import-classes', action='store_true', help='Import class files and their decompiled sources')
    
    args = parser.parse_args()
    
    importer = DataImporter(args.database_url)
    
    try:
        # Import services first
        if args.all or args.services_csv:
            if not args.services_csv:
                args.services_csv = '../work/prod/server_info.csv'
            importer.import_services_from_csv(args.services_csv, args.service_filter)
        
        # Import JAR files and their decompiled sources
        if args.all or args.import_jars or args.jar_csv:
            if not args.jar_csv:
                args.jar_csv = '../work/output/jar_analysis_report_20251007.csv'
            if not args.lib_decompile_dir:
                args.lib_decompile_dir = '../work/prod/lib-decompile'
            
            logger.info("=== Importing JAR files and their decompiled sources ===")
            importer.import_jar_files_from_csv(args.jar_csv, args.service_filter)
            importer.import_java_source_files_from_jars(args.lib_decompile_dir, args.jar_csv, args.service_filter)
        
        # Import class files and their decompiled sources
        if args.all or args.import_classes or args.classes_csv:
            if not args.classes_csv:
                args.classes_csv = '../work/output/classes_analysis_report_20251007.csv'
            if not args.classes_decompile_dir:
                args.classes_decompile_dir = '../work/prod/classes-decompile'
            
            logger.info("=== Importing class files and their decompiled sources ===")
            importer.import_java_source_files_from_classes(args.classes_decompile_dir, args.classes_csv, args.service_filter)
        
        logger.info("Data import completed successfully!")
        
    except Exception as e:
        logger.error(f"Data import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
