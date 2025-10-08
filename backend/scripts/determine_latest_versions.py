#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Latest Version Determination Script
Determines the latest version of each Java class across all services
"""

import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import logging

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import JavaSourceFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LatestVersionDeterminer:
    """Determines latest versions of Java classes across all services"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def determine_latest_versions(self):
        """Determine latest versions for all Java classes"""
        logger.info("Starting latest version determination...")
        
        db = self.get_db_session()
        
        try:
            # First, reset all is_latest flags to False
            logger.info("Resetting all is_latest flags...")
            db.query(JavaSourceFile).update({"is_latest": False})
            db.commit()
            
            # Get all unique class names
            class_names = db.query(JavaSourceFile.class_full_name).distinct().all()
            total_classes = len(class_names)
            logger.info(f"Found {total_classes} unique Java classes")
            
            updated_count = 0
            
            for i, (class_name,) in enumerate(class_names):
                try:
                    # Find the file with the latest modification time for this class
                    latest_file = db.query(JavaSourceFile).filter(
                        JavaSourceFile.class_full_name == class_name
                    ).order_by(JavaSourceFile.last_modified.desc()).first()
                    
                    if latest_file:
                        # Mark this file as the latest version
                        latest_file.is_latest = True
                        db.commit()
                        updated_count += 1
                        
                        logger.debug(f"Set latest version for {class_name}: {latest_file.service_id}")
                    
                    # Progress logging
                    if (i + 1) % 100 == 0 or i == total_classes - 1:
                        progress = ((i + 1) / total_classes) * 100
                        logger.info(f"Progress: {progress:.1f}% ({i + 1}/{total_classes})")
                
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing class {class_name}: {e}")
            
            logger.info(f"Successfully determined latest versions for {updated_count} classes")
            
            # Verify results
            latest_count = db.query(JavaSourceFile).filter(JavaSourceFile.is_latest == True).count()
            logger.info(f"Total files marked as latest: {latest_count}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in latest version determination: {e}")
            raise
        finally:
            db.close()
    
    def get_class_statistics(self):
        """Get statistics about classes and their versions"""
        db = self.get_db_session()
        
        try:
            # Total classes
            total_classes = db.query(JavaSourceFile.class_full_name).distinct().count()
            
            # Total files
            total_files = db.query(JavaSourceFile).count()
            
            # Latest files
            latest_files = db.query(JavaSourceFile).filter(JavaSourceFile.is_latest == True).count()
            
            # Classes with multiple versions
            multi_version_classes = db.query(JavaSourceFile.class_full_name).group_by(
                JavaSourceFile.class_full_name
            ).having(func.count(JavaSourceFile.id) > 1).count()
            
            logger.info("=== Class Statistics ===")
            logger.info(f"Total unique classes: {total_classes}")
            logger.info(f"Total Java source files: {total_files}")
            logger.info(f"Latest version files: {latest_files}")
            logger.info(f"Classes with multiple versions: {multi_version_classes}")
            
            return {
                'total_classes': total_classes,
                'total_files': total_files,
                'latest_files': latest_files,
                'multi_version_classes': multi_version_classes
            }
            
        finally:
            db.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Determine latest versions of Java classes')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics, do not update')
    
    args = parser.parse_args()
    
    determiner = LatestVersionDeterminer(args.database_url)
    
    try:
        if args.stats_only:
            determiner.get_class_statistics()
        else:
            determiner.determine_latest_versions()
            determiner.get_class_statistics()
        
        logger.info("Latest version determination completed successfully!")
        
    except Exception as e:
        logger.error(f"Latest version determination failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
