#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version Management Script for Java Library Analyzer
Manages JAR and Class file versions based on file size changes
"""

import os
import sys
import logging
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
    
    def generate_jar_versions(self, service_name=None):
        """Generate versions for JAR files based on file size changes"""
        logger.info("Starting JAR version generation...")
        
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
            
            # Group by jar_name
            jar_groups = defaultdict(list)
            for jar_file in jar_files:
                jar_groups[jar_file.jar_name].append(jar_file)
            
            logger.info(f"Found {len(jar_groups)} unique JAR names")
            
            total_updated = 0
            
            for jar_name, jars in jar_groups.items():
                # Sort by last_modified (ascending)
                jars.sort(key=lambda x: x.last_modified or x.created_at)
                
                # Generate versions based on file size changes
                versions = self._generate_versions_by_size(jars)
                
                # Update database
                for jar_file, version_no in zip(jars, versions):
                    jar_file.version_no = version_no
                    total_updated += 1
                
                logger.info(f"JAR {jar_name}: {len(jars)} files, versions {min(versions)}-{max(versions)}")
            
            # Set last_version_no for each jar_name
            self._set_last_versions(db, 'jar_files', 'jar_name')
            
            db.commit()
            logger.info(f"JAR version generation completed: {total_updated} files updated")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during JAR version generation: {e}")
            raise
        finally:
            db.close()
    
    def generate_class_versions(self, service_name=None):
        """Generate versions for Class files based on file size changes"""
        logger.info("Starting Class version generation...")
        
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
            
            for class_name, classes in class_groups.items():
                # Sort by last_modified (ascending)
                classes.sort(key=lambda x: x.last_modified or x.created_at)
                
                # Generate versions based on file size changes
                versions = self._generate_versions_by_size(classes)
                
                # Update database
                for class_file, version_no in zip(classes, versions):
                    class_file.version_no = version_no
                    total_updated += 1
                
                logger.info(f"Class {class_name}: {len(classes)} files, versions {min(versions)}-{max(versions)}")
            
            # Set last_version_no for each class_full_name
            self._set_last_versions(db, 'class_files', 'class_full_name')
            
            db.commit()
            logger.info(f"Class version generation completed: {total_updated} files updated")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during Class version generation: {e}")
            raise
        finally:
            db.close()
    
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
        
        # Update last_version_no
        for result in results:
            if table_name == 'jar_files':
                db.query(JarFile).filter(
                    JarFile.jar_name == result.jar_name
                ).update({'last_version_no': result.max_version})
            else:  # class_files
                db.query(ClassFile).filter(
                    ClassFile.class_full_name == result.class_full_name
                ).update({'last_version_no': result.max_version})
        
        logger.info(f"Updated last_version_no for {len(results)} {table_name}")
    
    def merge_source_versions(self, service_name=None):
        """Merge java_source_file_version_id for files with same version_no"""
        logger.info("Starting source version merging...")
        
        db = self.get_db_session()
        
        try:
            # Merge JAR source versions
            jar_merged = self._merge_jar_source_versions(db, service_name)
            
            # Merge Class source versions
            class_merged = self._merge_class_source_versions(db, service_name)
            
            db.commit()
            logger.info(f"Source version merging completed: {jar_merged} JAR mappings, {class_merged} Class files updated")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during source version merging: {e}")
            raise
        finally:
            db.close()
    
    def _merge_jar_source_versions(self, db, service_name=None):
        """Merge java_source_file_version_id for JAR files with same version_no"""
        logger.info("Merging JAR source versions...")
        
        # Get JAR files grouped by jar_name and version_no
        query = db.query(JarFile).filter(JarFile.version_no.isnot(None))
        if service_name:
            service = db.query(Service).filter(Service.service_name == service_name).first()
            if service:
                query = query.filter(JarFile.service_id == service.id)
        
        jar_files = query.order_by(JarFile.jar_name, JarFile.version_no, JarFile.last_modified).all()
        
        # Group by (jar_name, version_no)
        groups = defaultdict(list)
        for jar_file in jar_files:
            groups[(jar_file.jar_name, jar_file.version_no)].append(jar_file)
        
        merged_count = 0
        
        for (jar_name, version_no), jars in groups.items():
            if len(jars) <= 1:
                continue
            
            # Use the first JAR's source mappings for all JARs with same version
            first_jar = jars[0]
            other_jars = jars[1:]
            
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
            
            logger.info(f"JAR {jar_name} v{version_no}: merged {len(other_jars)} files")
        
        return merged_count
    
    def _merge_class_source_versions(self, db, service_name=None):
        """Merge java_source_file_version_id for Class files with same version_no"""
        logger.info("Merging Class source versions...")
        
        # Get Class files grouped by class_full_name and version_no
        query = db.query(ClassFile).filter(ClassFile.version_no.isnot(None))
        if service_name:
            service = db.query(Service).filter(Service.service_name == service_name).first()
            if service:
                query = query.filter(ClassFile.service_id == service.id)
        
        class_files = query.order_by(ClassFile.class_full_name, ClassFile.version_no, ClassFile.last_modified).all()
        
        # Group by (class_full_name, version_no)
        groups = defaultdict(list)
        for class_file in class_files:
            groups[(class_file.class_full_name, class_file.version_no)].append(class_file)
        
        merged_count = 0
        
        for (class_name, version_no), classes in groups.items():
            if len(classes) <= 1:
                continue
            
            # Use the first Class's source version for all Classes with same version
            first_class = classes[0]
            other_classes = classes[1:]
            
            if first_class.java_source_file_version_id:
                for other_class in other_classes:
                    other_class.java_source_file_version_id = first_class.java_source_file_version_id
                    merged_count += 1
                
                logger.info(f"Class {class_name} v{version_no}: merged {len(other_classes)} files")
        
        return merged_count
    
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
    parser.add_argument('--generate-jar-versions', action='store_true', help='Generate JAR versions')
    parser.add_argument('--generate-class-versions', action='store_true', help='Generate Class versions')
    parser.add_argument('--merge-sources', action='store_true', help='Merge source versions')
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
                manager.generate_jar_versions(args.service_name)
            
            if args.generate_class_versions:
                manager.generate_class_versions(args.service_name)
            
            if args.merge_sources:
                manager.merge_source_versions(args.service_name)
            
            if not any([args.generate_jar_versions, args.generate_class_versions, args.merge_sources]):
                logger.info("No action specified. Use --generate-jar-versions, --generate-class-versions, or --merge-sources")
        
        logger.info("Operation completed successfully!")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
