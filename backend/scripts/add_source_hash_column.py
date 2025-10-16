#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Script: Add source_hash column to jar_files table
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add the parent directory to the path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_source_hash_column(database_url):
    """Add source_hash column to jar_files table"""
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'jar_files' 
                AND COLUMN_NAME = 'source_hash'
            """)).fetchone()
            
            if result.count > 0:
                logger.info("Column 'source_hash' already exists in jar_files table")
                return True
            
            # Add the column
            logger.info("Adding source_hash column to jar_files table...")
            conn.execute(text("""
                ALTER TABLE jar_files 
                ADD COLUMN source_hash VARCHAR(64) NULL,
                ADD INDEX idx_jar_files_source_hash (source_hash)
            """))
            conn.commit()
            
            logger.info("Successfully added source_hash column to jar_files table")
            return True
            
    except Exception as e:
        logger.error(f"Error adding source_hash column: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add source_hash column to jar_files table')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    
    args = parser.parse_args()
    
    try:
        success = add_source_hash_column(args.database_url)
        if success:
            logger.info("Migration completed successfully!")
        else:
            logger.error("Migration failed!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
