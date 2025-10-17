#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version Management Script for Java Library Analyzer
Manages JAR and Class file versions based on file size changes or source content hash
"""

import os
import sys
import logging
import hashlib
from collections import defaultdict
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import Service, JarFile, ClassFile, JavaSourceFileVersion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VersionManager:
    """Version manager for JAR and Class files"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def generate_jar_versions(self, service_name=None, compares_by='file-size'):
        """Generate versions for JAR files based on file size changes or source content hash and merge source mappings"""
        logger.info(f"Starting JAR version generation and source merging (compares-by: {compares_by})...")
        
        db = self.get_db_session()
        
        try:
            # Get all non-third-party JAR files
            query = db.query(JarFile).filter(JarFile.is_third_party == False)
            if service_name:
                service = db.query(Service).filter(Service.service_name == service_name).first()
                if not service:
                    logger.error(f"Service {service_name} not found")
                    return False
                query = query.filter(JarFile.service_id == service.id)
            
            jar_files = query.all()
            logger.info(f"Found {len(jar_files)} non-third-party JAR files")
            
            # If compares_by is source-hash, calculate source hashes first
            if compares_by == 'source-hash':
                logger.info("Calculating source hashes for all JAR files...")
                self._calculate_source_hashes(db, jar_files)
                db.commit()  # Commit source hash updates
                logger.info("Source hash calculation completed")
            
            # Group by jar_name
            jar_groups = defaultdict(list)
            for jar_file in jar_files:
                jar_groups[jar_file.jar_name].append(jar_file)
            
            logger.info(f"Found {len(jar_groups)} unique JAR names")
            
            total_updated = 0
            total_merged = 0
            
            for jar_name, jars in jar_groups.items():
                # Sort by last_modified (ascending)
                jars.sort(key=lambda x: x.last_modified or x.created_at)
                
                # Generate versions based on comparison method
                if compares_by == 'source-hash':
                    versions = self._generate_versions_by_source_hash(jars)
                else:  # file-size
                    versions = self._generate_versions_by_size(jars)
                
                # Update database and merge source mappings
                merged_count = self._update_jar_versions_and_merge_sources(db, jars, versions)
                
                total_updated += len(jars)
                total_merged += merged_count
                
                logger.info(f"JAR {jar_name}: {len(jars)} files, versions {min(versions)}-{max(versions)}, {merged_count} source mappings merged")
            
            # Set last_version_no for each jar_name
            self._set_last_versions(db, 'jar_files', 'jar_name')
            
            db.commit()
            logger.info(f"JAR version generation completed: {total_updated} files updated, {total_merged} source mappings merged")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during JAR version generation: {e}")
            raise
        finally:
            db.close()
    
    def generate_class_versions(self, service_name=None):
        """Generate versions for Class files based on file size changes and merge source mappings"""
        logger.info("Starting Class version generation and source merging...")
        
        db = self.get_db_session()
        
        try:
            # Get all Class files
            query = db.query(ClassFile)
            if service_name:
                service = db.query(Service).filter(Service.service_name == service_name).first()
                if not service:
                    logger.error(f"Service {service_name} not found")
                    return False
                query = query.filter(ClassFile.service_id == service.id)
            
            class_files = query.all()
            logger.info(f"Found {len(class_files)} Class files")
            
            # Group by class_full_name
            class_groups = defaultdict(list)
            for class_file in class_files:
                class_groups[class_file.class_full_name].append(class_file)
            
            logger.info(f"Found {len(class_groups)} unique class names")
            
            total_updated = 0
            total_merged = 0
            
            for class_name, classes in class_groups.items():
                # Sort by last_modified (ascending)
                classes.sort(key=lambda x: x.last_modified or x.created_at)
                
                # Generate versions based on file size changes
                versions = self._generate_versions_by_size(classes)
                
                # Update database and merge source mappings
                merged_count = self._update_class_versions_and_merge_sources(db, classes, versions)
                
                total_updated += len(classes)
                total_merged += merged_count
                
                logger.info(f"Class {class_name}: {len(classes)} files, versions {min(versions)}-{max(versions)}, {merged_count} source mappings merged")
            
            # Set last_version_no for each class_full_name
            self._set_last_versions(db, 'class_files', 'class_full_name')
            
            db.commit()
            logger.info(f"Class version generation completed: {total_updated} files updated, {total_merged} source mappings merged")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during Class version generation: {e}")
            raise
        finally:
            db.close()
    
    def _calculate_source_hashes(self, db, jar_files):
        """Calculate source hash for all JAR files"""
        logger.info("Clearing existing source hashes...")
        
        # Clear all existing source hashes
        db.query(JarFile).update({'source_hash': None})
        
        logger.info("Calculating new source hashes...")
        
        for jar_file in jar_files:
            # Get all source files for this JAR
            source_mappings = db.execute(text("""
                SELECT jsf.class_full_name, jsfv.file_hash
                FROM java_source_in_jar_files jsij
                JOIN java_source_file_versions jsfv ON jsij.java_source_file_version_id = jsfv.id
                JOIN java_source_files jsf ON jsfv.java_source_file_id = jsf.id
                WHERE jsij.jar_file_id = :jar_id
                ORDER BY jsf.class_full_name ASC
            """), {"jar_id": jar_file.id}).fetchall()
            
            if not source_mappings:
                # No source files found, use file_size as fallback for hash calculation
                logger.warning(f"No source files found for JAR {jar_file.jar_name} (ID: {jar_file.id}), using file_size as fallback")
                file_size = jar_file.file_size or 0
                source_hash = hashlib.sha256(f"file_size:{file_size}".encode('utf-8')).hexdigest()
                jar_file.source_hash = source_hash
                logger.debug(f"JAR {jar_file.jar_name}: no source files, using file_size {file_size}, hash: {source_hash[:8]}...")
            else:
                # Build hash input string from source files
                hash_input_parts = []
                for mapping in source_mappings:
                    class_name = mapping.class_full_name or ""
                    file_hash = mapping.file_hash or ""
                    hash_input_parts.append(f"{class_name}:{file_hash}")
                
                # Calculate source hash
                hash_input = "\n".join(hash_input_parts)
                source_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                
                # Update JAR file with source hash
                jar_file.source_hash = source_hash
                
                logger.debug(f"JAR {jar_file.jar_name}: {len(source_mappings)} source files, hash: {source_hash[:8]}...")
    
    def _generate_versions_by_size(self, files):
        """Generate version numbers based on file size - same size = same version"""
        if not files:
            return []
        
        # Create a mapping of file size to version number
        size_to_version = {}
        current_version = 1
        
        # First pass: assign version numbers to unique sizes
        for file_obj in files:
            current_size = file_obj.file_size or 0
            if current_size not in size_to_version:
                size_to_version[current_size] = current_version
                current_version += 1
        
        # Second pass: assign version numbers to files based on their size
        versions = []
        for file_obj in files:
            current_size = file_obj.file_size or 0
            versions.append(size_to_version[current_size])
        
        return versions
    
    def _generate_versions_by_source_hash(self, files):
        """Generate version numbers based on source hash - same hash = same version"""
        if not files:
            return []
        
        # Create a mapping of source hash to version number
        hash_to_version = {}
        current_version = 1
        
        # First pass: assign version numbers to unique hashes
        for file_obj in files:
            current_hash = file_obj.source_hash
            if current_hash and current_hash not in hash_to_version:
                hash_to_version[current_hash] = current_version
                current_version += 1
        
        # Second pass: assign version numbers to files based on their hash
        versions = []
        for file_obj in files:
            current_hash = file_obj.source_hash
            if current_hash:
                versions.append(hash_to_version[current_hash])
            else:
                # If no hash, assign a unique version
                versions.append(current_version)
                current_version += 1
        
        return versions
    
    def _update_jar_versions_and_merge_sources(self, db, jars, versions):
        """Update JAR versions and merge source mappings in one pass"""
        merged_count = 0
        
        # Group jars by version number
        version_groups = defaultdict(list)
        for jar_file, version_no in zip(jars, versions):
            jar_file.version_no = version_no
            version_groups[version_no].append(jar_file)
        
        # For each version group, merge source mappings
        for version_no, version_jars in version_groups.items():
            if len(version_jars) <= 1:
                continue
            
            # Use the first JAR's source mappings for all JARs with same version
            first_jar = version_jars[0]
            other_jars = version_jars[1:]
            
            # Get source mappings for first JAR
            first_mappings = db.execute(text("""
                SELECT java_source_file_version_id 
                FROM java_source_in_jar_files 
                WHERE jar_file_id = :jar_id
            """), {"jar_id": first_jar.id}).fetchall()
            
            if not first_mappings:
                continue
            
            # Copy mappings to other JARs
            for other_jar in other_jars:
                # Delete existing mappings
                db.execute(text("""
                    DELETE FROM java_source_in_jar_files 
                    WHERE jar_file_id = :jar_id
                """), {"jar_id": other_jar.id})
                
                # Insert new mappings
                for mapping in first_mappings:
                    db.execute(text("""
                        INSERT INTO java_source_in_jar_files (jar_file_id, java_source_file_version_id)
                        VALUES (:jar_id, :source_version_id)
                        ON DUPLICATE KEY UPDATE jar_file_id = jar_file_id
                    """), {
                        "jar_id": other_jar.id,
                        "source_version_id": mapping.java_source_file_version_id
                    })
                
                merged_count += 1
        
        return merged_count
    
    def _update_class_versions_and_merge_sources(self, db, classes, versions):
        """Update Class versions and merge source mappings in one pass"""
        merged_count = 0
        
        # Group classes by version number
        version_groups = defaultdict(list)
        for class_file, version_no in zip(classes, versions):
            class_file.version_no = version_no
            version_groups[version_no].append(class_file)
        
        # For each version group, merge source mappings
        for version_no, version_classes in version_groups.items():
            if len(version_classes) <= 1:
                continue
            
            # Use the first Class's source version for all Classes with same version
            first_class = version_classes[0]
            other_classes = version_classes[1:]
            
            if first_class.java_source_file_version_id:
                for other_class in other_classes:
                    other_class.java_source_file_version_id = first_class.java_source_file_version_id
                    merged_count += 1
        
        return merged_count
    
    def _set_last_versions(self, db, table_name, name_column):
        """Set last_version_no for each unique name"""
        logger.info(f"Setting last_version_no for {table_name}...")
        
        # Get max version for each name
        if table_name == 'jar_files':
            query = db.query(
                JarFile.jar_name,
                func.max(JarFile.version_no).label('max_version')
            ).group_by(JarFile.jar_name)
        else:  # class_files
            query = db.query(
                ClassFile.class_full_name,
                func.max(ClassFile.version_no).label('max_version')
            ).group_by(ClassFile.class_full_name)
        
        results = query.all()
        
        # Update last_version_no for each unique name
        for result in results:
            if table_name == 'jar_files':
                # Update all files with the same jar_name
                db.query(JarFile).filter(
                    JarFile.jar_name == result.jar_name
                ).update({'last_version_no': result.max_version})
                logger.debug(f"Updated {result.jar_name}: last_version_no = {result.max_version}")
            else:  # class_files
                # Update all files with the same class_full_name
                db.query(ClassFile).filter(
                    ClassFile.class_full_name == result.class_full_name
                ).update({'last_version_no': result.max_version})
                logger.debug(f"Updated {result.class_full_name}: last_version_no = {result.max_version}")
        
        logger.info(f"Updated last_version_no for {len(results)} unique {table_name}")
    
    
    def get_version_statistics(self, service_name=None):
        """Get version statistics"""
        logger.info("Getting version statistics...")
        
        db = self.get_db_session()
        
        try:
            stats = {}
            
            # JAR statistics
            jar_query = db.query(JarFile).filter(JarFile.is_third_party == False)
            if service_name:
                service = db.query(Service).filter(Service.service_name == service_name).first()
                if service:
                    jar_query = jar_query.filter(JarFile.service_id == service.id)
            
            jar_count = jar_query.count()
            jar_versions = db.query(func.count(func.distinct(JarFile.jar_name))).filter(JarFile.is_third_party == False).scalar()
            
            stats['jars'] = {
                'total_files': jar_count,
                'unique_names': jar_versions,
                'with_versions': jar_query.filter(JarFile.version_no.isnot(None)).count()
            }
            
            # Class statistics
            class_query = db.query(ClassFile)
            if service_name:
                service = db.query(Service).filter(Service.service_name == service_name).first()
                if service:
                    class_query = class_query.filter(ClassFile.service_id == service.id)
            
            class_count = class_query.count()
            class_versions = db.query(func.count(func.distinct(ClassFile.class_full_name))).scalar()
            
            stats['classes'] = {
                'total_files': class_count,
                'unique_names': class_versions,
                'with_versions': class_query.filter(ClassFile.version_no.isnot(None)).count()
            }
            
            return stats
            
        finally:
            db.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage JAR and Class file versions')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', help='Process specific service only')
    parser.add_argument('--generate-jar-versions', action='store_true', help='Generate JAR versions and merge source mappings')
    parser.add_argument('--generate-class-versions', action='store_true', help='Generate Class versions and merge source mappings')
    parser.add_argument('--compares-by', choices=['file-size', 'source-hash'], default='file-size',
                       help='Comparison method for version generation (default: file-size)')
    parser.add_argument('--stats-only', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    manager = VersionManager(args.database_url)
    
    try:
        if args.stats_only:
            stats = manager.get_version_statistics(args.service_name)
            logger.info("=== Version Statistics ===")
            logger.info(f"JARs: {stats['jars']['total_files']} files, {stats['jars']['unique_names']} unique names, {stats['jars']['with_versions']} with versions")
            logger.info(f"Classes: {stats['classes']['total_files']} files, {stats['classes']['unique_names']} unique names, {stats['classes']['with_versions']} with versions")
        else:
            if args.generate_jar_versions:
                manager.generate_jar_versions(args.service_name, args.compares_by)
            
            if args.generate_class_versions:
                manager.generate_class_versions(args.service_name)
            
            if not any([args.generate_jar_versions, args.generate_class_versions]):
                logger.info("No action specified. Use --generate-jar-versions or --generate-class-versions")
        
        logger.info("Operation completed successfully!")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
