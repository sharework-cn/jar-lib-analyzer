#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JAR Files Decompiler Script
Decompile JAR files for services and save to output directories
"""

import os
import sys
import argparse
import logging
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import paramiko
from scp import SCPClient

# Try to import tqdm for better progress bar, fallback to simple version
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, JarFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JarDecompiler:
    """JAR file decompiler"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.cfr_jar = "assets/jar/cfr-0.152.jar"
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def download_jar_from_server(self, service, jar_file):
        """Download JAR file from server"""
        try:
            # Create SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            ssh.connect(
                hostname=service.ip_address,
                port=service.port,
                username=service.username,
                password=service.password,
                timeout=30
            )
            
            # Build remote file path
            server_base_path = service.server_base_path or ''
            jar_path = service.jar_path.replace('{service_name}', service.service_name)
            jar_path = jar_path.replace('{server_base_path}', server_base_path)
            remote_file_path = os.path.join(jar_path, jar_file.jar_name).replace('\\', '/')
            
            # Create local directory
            local_dir = os.path.join(service.jar_decompile_output_dir, "_jar", f"{service.service_name}@{service.ip_address}").replace('\\', '/')
            os.makedirs(local_dir, exist_ok=True)
            
            # Download file
            local_file_path = os.path.join(local_dir, jar_file.jar_name)
            
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_file_path, local_file_path)
            
            ssh.close()
            
            logger.info(f"Downloaded JAR: {jar_file.jar_name} from {service.service_name}")
            return local_file_path
            
        except Exception as e:
            logger.error(f"Failed to download JAR {jar_file.jar_name} from {service.service_name}: {e}")
            return None
    
    def copy_jar_from_local(self, service, jar_file):
        """Copy JAR file from local directory"""
        try:
            # Build local file path
            server_base_path = service.server_base_path or ''
            jar_path = service.jar_path.replace('{service_name}', service.service_name)
            jar_path = jar_path.replace('{server_base_path}', server_base_path)
            local_file_path = os.path.join(jar_path, jar_file.jar_name)
            
            if not os.path.exists(local_file_path):
                logger.warning(f"Local JAR file not found: {local_file_path}")
                return None
            
            # Create local directory
            local_dir = os.path.join(service.jar_decompile_output_dir, "_jar", f"{service.service_name}@{service.ip_address}").replace('\\', '/')
            os.makedirs(local_dir, exist_ok=True)
            
            # Copy file
            target_file_path = os.path.join(local_dir, jar_file.jar_name)
            shutil.copy2(local_file_path, target_file_path)
            
            logger.info(f"Copied JAR: {jar_file.jar_name} for {service.service_name}")
            return target_file_path
            
        except Exception as e:
            logger.error(f"Failed to copy JAR {jar_file.jar_name} for {service.service_name}: {e}")
            return None
    
    def decompile_jar(self, jar_file_path, service, jar_file):
        """Decompile JAR file using CFR"""
        try:
            # Create decompile output directory using last_modified date
            jar_name_without_ext = jar_file.jar_name.replace('.jar', '')
            # Use last_modified date from database
            if jar_file.last_modified:
                date_str = jar_file.last_modified.strftime("%Y%m%d")
            else:
                # Fallback to current date if last_modified is None
                date_str = datetime.now().strftime("%Y%m%d")
            decompile_dir = os.path.join(
                service.jar_decompile_output_dir,
                jar_name_without_ext,
                f"{date_str}-{service.service_name}@{service.ip_address}"
            ).replace('\\', '/')
            os.makedirs(decompile_dir, exist_ok=True)
            
            # Execute decompile command
            command = [
                'java', '-jar', self.cfr_jar,
                jar_file_path,
                '--outputdir', decompile_dir
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Decompiled JAR: {jar_file.jar_name} -> {decompile_dir}")
                return decompile_dir
            else:
                logger.error(f"Decompilation failed for {jar_file.jar_name}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Decompilation failed for {jar_file.jar_name}: {e}")
            return None
    
    def decompile_jars_for_service(self, service_name, environment='production'):
        """Decompile JAR files for a specific service"""
        logger.info(f"Decompiling JAR files for service: {service_name} ({environment})")
        
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
            
            # Get JAR files for this service
            jar_files = db.query(JarFile).filter(JarFile.service_id == service.id).all()
            
            if not jar_files:
                logger.warning(f"No JAR files found for service: {service_name}")
                return True
            
            logger.info(f"Found {len(jar_files)} JAR files for service: {service_name}")
            
            successful_decompiles = 0
            
            # Process JAR files with progress tracking
            if HAS_TQDM:
                # Use tqdm for better progress bar
                with tqdm(total=len(jar_files), desc=f"Decompiling {service_name}", unit="jar") as pbar:
                    for jar_file in jar_files:
                        try:
                            # Skip third-party JAR files
                            if jar_file.is_third_party:
                                logger.debug(f"Skipping third-party JAR: {jar_file.jar_name}")
                                pbar.update(1)
                                continue
                            
                            # Download or copy JAR file
                            if service.username and service.password:
                                jar_file_path = self.download_jar_from_server(service, jar_file)
                            else:
                                jar_file_path = self.copy_jar_from_local(service, jar_file)
                            
                            if not jar_file_path:
                                pbar.update(1)
                                continue
                            
                            # Decompile JAR file
                            decompile_dir = self.decompile_jar(jar_file_path, service, jar_file)
                            
                            if decompile_dir:
                                successful_decompiles += 1
                                # Update JAR file record with local path
                                jar_file.file_path = jar_file_path
                                db.commit()
                            
                            pbar.update(1)
                        
                        except Exception as e:
                            logger.error(f"Error processing JAR {jar_file.jar_name}: {e}")
                            pbar.update(1)
            else:
                # Fallback to simple progress tracking
                for idx, jar_file in enumerate(jar_files, 1):
                    try:
                        # Skip third-party JAR files
                        if jar_file.is_third_party:
                            logger.debug(f"Skipping third-party JAR: {jar_file.jar_name}")
                            continue
                        
                        # Download or copy JAR file
                        if service.username and service.password:
                            jar_file_path = self.download_jar_from_server(service, jar_file)
                        else:
                            jar_file_path = self.copy_jar_from_local(service, jar_file)
                        
                        if not jar_file_path:
                            continue
                        
                        # Decompile JAR file
                        decompile_dir = self.decompile_jar(jar_file_path, service, jar_file)
                        
                        if decompile_dir:
                            successful_decompiles += 1
                            # Update JAR file record with local path
                            jar_file.file_path = jar_file_path
                            db.commit()
                        
                        # Simple progress logging
                        progress = (idx / len(jar_files)) * 100
                        logger.info(f"Progress: {progress:.1f}% ({idx}/{len(jar_files)})")
                    
                    except Exception as e:
                        logger.error(f"Error processing JAR {jar_file.jar_name}: {e}")
            
            logger.info(f"Successfully decompiled {successful_decompiles}/{len(jar_files)} JAR files for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error decompiling JAR files for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def decompile_jars_for_all_services(self):
        """Decompile JAR files for all services"""
        logger.info("Decompiling JAR files for all services")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            # Process services with progress tracking
            if HAS_TQDM:
                # Use tqdm for better progress bar
                with tqdm(total=total_services, desc="Processing services", unit="service") as pbar:
                    for service in services:
                        logger.info(f"Processing service: {service.service_name} ({service.environment})")
                        
                        success = self.decompile_jars_for_service(service.service_name, service.environment)
                        if not success:
                            logger.error(f"Failed to decompile JAR files for service: {service.service_name}")
                        
                        pbar.update(1)
            else:
                # Fallback to simple progress tracking
                for idx, service in enumerate(services, 1):
                    logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                    
                    success = self.decompile_jars_for_service(service.service_name, service.environment)
                    if not success:
                        logger.error(f"Failed to decompile JAR files for service: {service.service_name}")
                    
                    # Show progress
                    progress = (idx / total_services) * 100
                    logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("JAR files decompilation completed for all services")
            
        except Exception as e:
            logger.error(f"Error decompiling JAR files for all services: {e}")
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Decompile JAR files for services')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Decompile JAR files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Decompile JAR files for all services')
    
    args = parser.parse_args()
    
    # Check if CFR tool exists
    cfr_jar = "assets/jar/cfr-0.152.jar"
    if not os.path.exists(cfr_jar):
        logger.error(f"CFR tool does not exist: {cfr_jar}")
        sys.exit(1)
    
    decompiler = JarDecompiler(args.database_url)
    
    try:
        if args.all_services:
            decompiler.decompile_jars_for_all_services()
        elif args.service_name:
            decompiler.decompile_jars_for_service(args.service_name, args.environment)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("JAR files decompilation completed successfully!")
        
    except Exception as e:
        logger.error(f"JAR files decompilation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
