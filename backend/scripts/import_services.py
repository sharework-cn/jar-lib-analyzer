#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Information Import Script
Import service information from JSON configuration file to database
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceImporter:
    """Service information importer"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def load_json_config(self, config_file_path):
        """Load service configuration from JSON file"""
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Successfully loaded configuration from {config_file_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration file {config_file_path}: {e}")
            raise
    
    def import_services_from_json(self, config_file_path, service_filter=None, environment_filter=None):
        """Import services from JSON configuration file"""
        logger.info(f"Importing services from {config_file_path}")
        
        try:
            # Load configuration
            config = self.load_json_config(config_file_path)
            
            # Validate configuration structure
            if 'services' not in config:
                raise ValueError("Configuration file must contain 'services' array")
            
            services_config = config['services']
            if not isinstance(services_config, list):
                raise ValueError("'services' must be an array")
            
            db = self.get_db_session()
            imported_count = 0
            updated_count = 0
            
            for service_config in services_config:
                try:
                    # Apply filters
                    if service_filter and service_config.get('service_name') != service_filter:
                        continue
                    if environment_filter and service_config.get('environment') != environment_filter:
                        continue
                    
                    # Check if service already exists
                    existing_service = db.query(Service).filter(
                        Service.service_name == service_config.get('service_name'),
                        Service.environment == service_config.get('environment', 'production')
                    ).first()
                    
                    # Prepare service data
                    service_data = {
                        'service_name': service_config.get('service_name'),
                        'environment': service_config.get('environment', 'production'),
                        'ip_address': service_config.get('ip_address'),
                        'port': service_config.get('port'),
                        'username': service_config.get('username'),
                        'password': service_config.get('password'),
                        'server_base_path': service_config.get('server_base_path'),
                        'jar_path': service_config.get('jar_path'),
                        'classes_path': service_config.get('classes_path'),
                        'source_path': service_config.get('source_path'),
                        'jar_info_file_path': service_config.get('jar_info_file_path'),
                        'class_info_file_path': service_config.get('class_info_file_path'),
                        'jar_decompile_output_dir': service_config.get('jar_decompile_output_dir'),
                        'class_decompile_output_dir': service_config.get('class_decompile_output_dir'),
                        'description': service_config.get('description')
                    }
                    
                    # Validate required fields
                    required_fields = ['service_name', 'jar_info_file_path', 'class_info_file_path', 
                                     'jar_decompile_output_dir', 'class_decompile_output_dir']
                    for field in required_fields:
                        if not service_data[field]:
                            raise ValueError(f"Required field '{field}' is missing or empty")
                    
                    if existing_service:
                        # Update existing service
                        for key, value in service_data.items():
                            setattr(existing_service, key, value)
                        updated_count += 1
                        logger.info(f"Updated service: {service_data['service_name']} ({service_data['environment']})")
                    else:
                        # Create new service
                        service = Service(**service_data)
                        db.add(service)
                        imported_count += 1
                        logger.info(f"Imported service: {service_data['service_name']} ({service_data['environment']})")
                    
                    db.commit()
                    
                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"Database integrity error for service {service_config.get('service_name')}: {e}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing service {service_config.get('service_name')}: {e}")
            
            db.close()
            logger.info(f"Successfully imported {imported_count} new services, updated {updated_count} existing services")
            
        except Exception as e:
            logger.error(f"Error importing services: {e}")
            raise
    
    def create_sample_config(self, output_file):
        """Create a sample configuration file"""
        sample_config = {
            "services": [
                {
                    "service_name": "dsop_gateway",
                    "environment": "production",
                    "ip_address": "10.20.151.32",
                    "port": 22,
                    "username": "",
                    "password": "",
                    "server_base_path": "/app/apprun/tomcat_server/webapps/dsop_gateway/WEB-INF",
                    "jar_path": "work/prod/lib-download/{service_name}{server_base_path}/lib",
                    "classes_path": "work/prod/classes-download/{service_name}{server_base_path}/classes",
                    "source_path": "tsm_2.0/tsm_gateway",
                    "jar_info_file_path": "work/prod/lib-list/dsop_gateway.txt",
                    "class_info_file_path": "work/prod/classes-list/dsop_gateway.txt",
                    "jar_decompile_output_dir": "work/prod/lib-decompile",
                    "class_decompile_output_dir": "work/prod/classes-decompile",
                    "description": "DSOP Gateway Service"
                },
                {
                    "service_name": "dsop_core",
                    "environment": "production",
                    "ip_address": "10.20.151.2",
                    "port": 22,
                    "username": "",
                    "password": "",
                    "server_base_path": "/app/apprun/tomcat_server/webapps/dsop_core/WEB-INF",
                    "jar_path": "work/prod/lib-download/{service_name}{server_base_path}/lib",
                    "classes_path": "work/prod/classes-download/{service_name}{server_base_path}/classes",
                    "source_path": "tsm_2.0/tsm_web",
                    "jar_info_file_path": "work/prod/lib-list/dsop_core.txt",
                    "class_info_file_path": "work/prod/classes-list/dsop_core.txt",
                    "jar_decompile_output_dir": "work/prod/lib-decompile",
                    "class_decompile_output_dir": "work/prod/classes-decompile",
                    "description": "DSOP Core Service"
                }
            ]
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            logger.info(f"Sample configuration file created: {output_file}")
        except Exception as e:
            logger.error(f"Error creating sample configuration file: {e}")
            raise

def get_config_file_path(args_config, env_config, default_config):
    """Get configuration file path with priority: args > env > default"""
    if args_config:
        return args_config
    elif env_config:
        return env_config
    else:
        return default_config

def main():
    parser = argparse.ArgumentParser(description='Import service information from JSON configuration')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--config-file', 
                       help='Path to service configuration JSON file')
    parser.add_argument('--service-filter', 
                       help='Only import specific service (e.g., dsop_gateway)')
    parser.add_argument('--environment-filter', 
                       help='Only import specific environment (e.g., production)')
    parser.add_argument('--create-sample', 
                       help='Create sample configuration file at specified path')
    
    args = parser.parse_args()
    
    # Get configuration file path
    env_config = os.getenv('SERVICE_CONFIG_FILE')
    default_config = 'work/prod/services_config.json'
    config_file = get_config_file_path(args.config_file, env_config, default_config)
    
    importer = ServiceImporter(args.database_url)
    
    try:
        if args.create_sample:
            # Create sample configuration file
            importer.create_sample_config(args.create_sample)
        else:
            # Import services
            if not os.path.exists(config_file):
                logger.error(f"Configuration file not found: {config_file}")
                logger.info("Use --create-sample to create a sample configuration file")
                sys.exit(1)
            
            importer.import_services_from_json(
                config_file, 
                args.service_filter, 
                args.environment_filter
            )
            logger.info("Service import completed successfully!")
        
    except Exception as e:
        logger.error(f"Service import failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
