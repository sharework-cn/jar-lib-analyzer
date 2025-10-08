#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orphaned Java Source Files Cleanup Script
Clean up Java source files that are no longer referenced by JAR or class files
"""

import os
import sys
import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, JarFile, ClassFile, JavaSourceFile, JavaSourceInJarFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrphanedSourceCleaner:
    """Orphaned Java source files cleaner"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def find_orphaned_sources(self):
        """Find orphaned Java source files"""
        logger.info("Finding orphaned Java source files...")
        
        db = self.get_db_session()
        
        try:
            # Find Java source files that are not referenced by any JAR or class files
            orphaned_sources = db.query(JavaSourceFile).filter(
                ~JavaSourceFile.id.in_(
                    db.query(JavaSourceInJarFile.java_source_file_id).union(
                        db.query(ClassFile.java_source_file_id).filter(ClassFile.java_source_file_id.isnot(None))
                    )
                )
            ).all()
            
            logger.info(f"Found {len(orphaned_sources)} orphaned Java source files")
            
            return orphaned_sources
            
        except Exception as e:
            logger.error(f"Error finding orphaned sources: {e}")
            return []
        finally:
            db.close()
    
    def cleanup_orphaned_sources(self, dry_run=True):
        """Clean up orphaned Java source files"""
        logger.info(f"Starting cleanup of orphaned Java source files (dry_run={dry_run})")
        
        orphaned_sources = self.find_orphaned_sources()
        
        if not orphaned_sources:
            logger.info("No orphaned Java source files found")
            return True
        
        db = self.get_db_session()
        
        try:
            deleted_count = 0
            
            for source_file in orphaned_sources:
                try:
                    logger.info(f"Orphaned source: {source_file.class_full_name} (ID: {source_file.id})")
                    
                    if not dry_run:
                        # Delete the orphaned source file
                        db.delete(source_file)
                        db.commit()
                        deleted_count += 1
                        logger.info(f"Deleted orphaned source: {source_file.class_full_name}")
                    else:
                        logger.info(f"[DRY RUN] Would delete: {source_file.class_full_name}")
                
                except Exception as e:
                    logger.error(f"Error deleting orphaned source {source_file.class_full_name}: {e}")
                    db.rollback()
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete {len(orphaned_sources)} orphaned Java source files")
            else:
                logger.info(f"Successfully deleted {deleted_count} orphaned Java source files")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False
        finally:
            db.close()
    
    def cleanup_orphaned_sources_for_service(self, service_name, environment='production', dry_run=True):
        """Clean up orphaned Java source files for a specific service"""
        logger.info(f"Starting cleanup of orphaned Java source files for service: {service_name} ({environment}) (dry_run={dry_run})")
        
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
            
            # Get JAR and class files for this service
            jar_files = db.query(JarFile).filter(JarFile.service_id == service.id).all()
            class_files = db.query(ClassFile).filter(ClassFile.service_id == service.id).all()
            
            jar_file_ids = [jf.id for jf in jar_files]
            class_file_ids = [cf.id for cf in class_files]
            
            # Find Java source files that are referenced by this service's JAR or class files
            referenced_source_ids = set()
            
            if jar_file_ids:
                jar_referenced = db.query(JavaSourceInJarFile.java_source_file_id).filter(
                    JavaSourceInJarFile.jar_file_id.in_(jar_file_ids)
                ).all()
                referenced_source_ids.update([r[0] for r in jar_referenced])
            
            if class_file_ids:
                class_referenced = db.query(ClassFile.java_source_file_id).filter(
                    ClassFile.id.in_(class_file_ids),
                    ClassFile.java_source_file_id.isnot(None)
                ).all()
                referenced_source_ids.update([r[0] for r in class_referenced])
            
            # Find orphaned sources for this service (sources that exist but are not referenced)
            orphaned_sources = db.query(JavaSourceFile).filter(
                ~JavaSourceFile.id.in_(referenced_source_ids)
            ).all()
            
            logger.info(f"Found {len(orphaned_sources)} orphaned Java source files for service: {service_name}")
            
            if not orphaned_sources:
                logger.info(f"No orphaned Java source files found for service: {service_name}")
                return True
            
            deleted_count = 0
            
            for source_file in orphaned_sources:
                try:
                    logger.info(f"Orphaned source for {service_name}: {source_file.class_full_name} (ID: {source_file.id})")
                    
                    if not dry_run:
                        # Delete the orphaned source file
                        db.delete(source_file)
                        db.commit()
                        deleted_count += 1
                        logger.info(f"Deleted orphaned source: {source_file.class_full_name}")
                    else:
                        logger.info(f"[DRY RUN] Would delete: {source_file.class_full_name}")
                
                except Exception as e:
                    logger.error(f"Error deleting orphaned source {source_file.class_full_name}: {e}")
                    db.rollback()
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete {len(orphaned_sources)} orphaned Java source files for service: {service_name}")
            else:
                logger.info(f"Successfully deleted {deleted_count} orphaned Java source files for service: {service_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def cleanup_orphaned_sources_for_all_services(self, dry_run=True):
        """Clean up orphaned Java source files for all services"""
        logger.info(f"Starting cleanup of orphaned Java source files for all services (dry_run={dry_run})")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            for idx, service in enumerate(services, 1):
                logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                
                success = self.cleanup_orphaned_sources_for_service(
                    service.service_name, 
                    service.environment, 
                    dry_run
                )
                if not success:
                    logger.error(f"Failed to cleanup orphaned sources for service: {service.service_name}")
                
                # Show progress
                progress = (idx / total_services) * 100
                logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("Orphaned sources cleanup completed for all services")
            
        except Exception as e:
            logger.error(f"Error during cleanup for all services: {e}")
        finally:
            db.close()
    
    def get_cleanup_statistics(self):
        """Get cleanup statistics"""
        logger.info("Getting cleanup statistics...")
        
        db = self.get_db_session()
        
        try:
            # Total Java source files
            total_sources = db.query(JavaSourceFile).count()
            
            # Referenced Java source files
            referenced_sources = db.query(JavaSourceFile).filter(
                JavaSourceFile.id.in_(
                    db.query(JavaSourceInJarFile.java_source_file_id).union(
                        db.query(ClassFile.java_source_file_id).filter(ClassFile.java_source_file_id.isnot(None))
                    )
                )
            ).count()
            
            # Orphaned Java source files
            orphaned_sources = total_sources - referenced_sources
            
            # JAR files count
            total_jar_files = db.query(JarFile).count()
            
            # Class files count
            total_class_files = db.query(ClassFile).count()
            
            # Services count
            total_services = db.query(Service).count()
            
            logger.info("=== Cleanup Statistics ===")
            logger.info(f"Total services: {total_services}")
            logger.info(f"Total JAR files: {total_jar_files}")
            logger.info(f"Total class files: {total_class_files}")
            logger.info(f"Total Java source files: {total_sources}")
            logger.info(f"Referenced Java source files: {referenced_sources}")
            logger.info(f"Orphaned Java source files: {orphaned_sources}")
            logger.info(f"Orphaned percentage: {(orphaned_sources/total_sources*100):.2f}%" if total_sources > 0 else "N/A")
            
            return {
                'total_services': total_services,
                'total_jar_files': total_jar_files,
                'total_class_files': total_class_files,
                'total_sources': total_sources,
                'referenced_sources': referenced_sources,
                'orphaned_sources': orphaned_sources
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup statistics: {e}")
            return None
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Clean up orphaned Java source files')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Clean up orphaned sources for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Clean up orphaned sources for all services')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Perform dry run (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually execute the cleanup (overrides --dry-run)')
    parser.add_argument('--statistics', action='store_true',
                       help='Show cleanup statistics only')
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = not args.execute if args.execute else args.dry_run
    
    cleaner = OrphanedSourceCleaner(args.database_url)
    
    try:
        if args.statistics:
            # Show statistics only
            cleaner.get_cleanup_statistics()
        elif args.all_services:
            cleaner.cleanup_orphaned_sources_for_all_services(dry_run)
        elif args.service_name:
            cleaner.cleanup_orphaned_sources_for_service(args.service_name, args.environment, dry_run)
        else:
            # Default: find all orphaned sources
            cleaner.cleanup_orphaned_sources(dry_run)
        
        if not args.statistics:
            logger.info("Orphaned sources cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Orphaned sources cleanup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
