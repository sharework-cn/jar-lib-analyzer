#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Cleanup Script for Source Code Difference Analysis System
Clears all data from the database
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataCleaner:
    """Data cleaner for the source code difference analysis system"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def clean_all_data(self):
        """Clean all data from the database"""
        logger.info("Starting data cleanup...")
        
        db = self.get_db_session()
        
        try:
            # Disable foreign key checks temporarily
            db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # Clear tables in reverse dependency order (excluding services table)
            # Order: child tables first, then parent tables
            tables_to_clear = [
                'source_differences',           # References: services, java_source_file_versions
                'java_source_in_jar_files',     # References: jar_files, java_source_file_versions
                'class_files',                  # References: services, java_source_file_versions
                'jar_files',                    # References: services
                'java_source_file_versions',    # References: java_source_files
                'java_source_files'             # No dependencies
            ]
            
            for table in tables_to_clear:
                logger.info(f"Clearing table: {table}")
                result = db.execute(text(f"DELETE FROM {table}"))
                logger.info(f"Cleared {result.rowcount} rows from {table}")
            
            # Reset auto-increment counters
            for table in tables_to_clear:
                db.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1"))
                logger.info(f"Reset auto-increment for {table}")
            
            # Re-enable foreign key checks
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            db.commit()
            logger.info("Data cleanup completed successfully!")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during data cleanup: {e}")
            raise
        finally:
            db.close()
    
    def get_table_counts(self):
        """Get current table counts"""
        db = self.get_db_session()
        
        try:
            tables = ['services', 'jar_files', 'class_files', 'java_source_files', 'java_source_file_versions', 'java_source_in_jar_files', 'source_differences']
            counts = {}
            
            for table in tables:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                counts[table] = count
                logger.info(f"Table {table}: {count} rows")
            
            return counts
            
        finally:
            db.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean data from Source Code Difference Analysis System')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics, do not clean')
    
    args = parser.parse_args()
    
    cleaner = DataCleaner(args.database_url)
    
    try:
        if args.stats_only:
            logger.info("=== Current Database Statistics ===")
            cleaner.get_table_counts()
        else:
            logger.info("=== Starting Data Cleanup ===")
            cleaner.get_table_counts()
            cleaner.clean_all_data()
            logger.info("=== Cleanup Complete ===")
            cleaner.get_table_counts()
        
        logger.info("Operation completed successfully!")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
