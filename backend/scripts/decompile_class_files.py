#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class Files Decompiler Script
Decompile class files for services and save to output directories
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

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import Service, ClassFile, Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClassDecompiler:
    """Class file decompiler"""
    
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.cfr_jar = "assets/jar/cfr-0.152.jar"
        
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def download_class_from_server(self, service, class_file):
        """Download class file from server"""
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
            classes_path = service.classes_path.replace('{service_name}', service.service_name)
            classes_path = classes_path.replace('{server_base_path}', server_base_path)
            
            # Convert class name to file path
            class_file_path = class_file.class_full_name.replace('.', '/') + '.class'
            remote_file_path = os.path.join(classes_path, class_file_path).replace('\\', '/')
            
            # Create local directory
            local_dir = os.path.join(service.class_decompile_output_dir, "_class", f"{service.service_name}@{service.ip_address}").replace('\\', '/')
            os.makedirs(local_dir, exist_ok=True)
            
            # Download file
            local_file_path = os.path.join(local_dir, class_file.class_full_name.replace('.', '_') + '.class')
            
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_file_path, local_file_path)
            
            ssh.close()
            
            logger.info(f"Downloaded class: {class_file.class_full_name} from {service.service_name}")
            return local_file_path
            
        except Exception as e:
            logger.error(f"Failed to download class {class_file.class_full_name} from {service.service_name}: {e}")
            return None
    
    def copy_class_from_local(self, service, class_file):
        """Copy class file from local directory"""
        try:
            # Build local file path
            server_base_path = service.server_base_path or ''
            classes_path = service.classes_path.replace('{service_name}', service.service_name)
            classes_path = classes_path.replace('{server_base_path}', server_base_path)
            
            # Convert class name to file path
            class_file_path = class_file.class_full_name.replace('.', '/') + '.class'
            local_file_path = os.path.join(classes_path, class_file_path)
            
            if not os.path.exists(local_file_path):
                logger.warning(f"Local class file not found: {local_file_path}")
                return None
            
            # Create local directory
            local_dir = os.path.join(service.class_decompile_output_dir, "_class", f"{service.service_name}@{service.ip_address}").replace('\\', '/')
            os.makedirs(local_dir, exist_ok=True)
            
            # Copy file
            target_file_path = os.path.join(local_dir, class_file.class_full_name.replace('.', '_') + '.class')
            shutil.copy2(local_file_path, target_file_path)
            
            logger.info(f"Copied class: {class_file.class_full_name} for {service.service_name}")
            return target_file_path
            
        except Exception as e:
            logger.error(f"Failed to copy class {class_file.class_full_name} for {service.service_name}: {e}")
            return None
    
    def decompile_class(self, class_file_path, service, class_file):
        """Decompile class file using CFR"""
        try:
            # Create decompile output directory using last_modified date
            class_name = class_file.class_full_name
            # Use last_modified date from database
            if class_file.last_modified:
                date_str = class_file.last_modified.strftime("%Y%m%d")
            else:
                # Fallback to current date if last_modified is None
                date_str = datetime.now().strftime("%Y%m%d")
            decompile_dir = os.path.join(
                service.class_decompile_output_dir,
                class_name,
                f"{date_str}-{service.service_name}@{service.ip_address}"
            ).replace('\\', '/')
            os.makedirs(decompile_dir, exist_ok=True)
            
            # Execute decompile command
            command = [
                'java', '-jar', self.cfr_jar,
                class_file_path,
                '--outputdir', decompile_dir
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Decompiled class: {class_file.class_full_name} -> {decompile_dir}")
                # Update decompile_path in database
                class_file.decompile_path = os.path.join(
                    service.class_decompile_output_dir,
                    class_name
                ).replace('\\', '/')
                return decompile_dir
            else:
                logger.error(f"Decompilation failed for {class_file.class_full_name}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Decompilation failed for {class_file.class_full_name}: {e}")
            return None
    
    def decompile_classes_for_service(self, service_name, environment='production'):
        """Decompile class files for a specific service"""
        logger.info(f"Decompiling class files for service: {service_name} ({environment})")
        
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
            
            # Get class files for this service
            class_files = db.query(ClassFile).filter(ClassFile.service_id == service.id).all()
            
            if not class_files:
                logger.warning(f"No class files found for service: {service_name}")
                return True
            
            logger.info(f"Found {len(class_files)} class files for service: {service_name}")
            
            successful_decompiles = 0
            
            for class_file in class_files:
                try:
                    # Download or copy class file
                    if service.username and service.password:
                        class_file_path = self.download_class_from_server(service, class_file)
                    else:
                        class_file_path = self.copy_class_from_local(service, class_file)
                    
                    if not class_file_path:
                        continue
                    
                    # Decompile class file
                    decompile_dir = self.decompile_class(class_file_path, service, class_file)
                    
                    if decompile_dir:
                        successful_decompiles += 1
                        # Update class file record with local path
                        class_file.file_path = class_file_path
                        db.commit()
                
                except Exception as e:
                    logger.error(f"Error processing class {class_file.class_full_name}: {e}")
            
            logger.info(f"Successfully decompiled {successful_decompiles}/{len(class_files)} class files for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error decompiling class files for service {service_name}: {e}")
            return False
        finally:
            db.close()
    
    def decompile_classes_for_all_services(self):
        """Decompile class files for all services"""
        logger.info("Decompiling class files for all services")
        
        db = self.get_db_session()
        
        try:
            services = db.query(Service).all()
            total_services = len(services)
            
            for idx, service in enumerate(services, 1):
                logger.info(f"[{idx}/{total_services}] Processing service: {service.service_name} ({service.environment})")
                
                success = self.decompile_classes_for_service(service.service_name, service.environment)
                if not success:
                    logger.error(f"Failed to decompile class files for service: {service.service_name}")
                
                # Show progress
                progress = (idx / total_services) * 100
                logger.info(f"Progress: {progress:.1f}%")
            
            logger.info("Class files decompilation completed for all services")
            
        except Exception as e:
            logger.error(f"Error decompiling class files for all services: {e}")
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description='Decompile class files for services')
    parser.add_argument('--database-url', default='mysql+pymysql://jal:271828@172.30.80.95:32306/jal',
                       help='Database connection URL')
    parser.add_argument('--service-name', 
                       help='Decompile class files for specific service only')
    parser.add_argument('--environment', default='production',
                       help='Environment filter (default: production)')
    parser.add_argument('--all-services', action='store_true',
                       help='Decompile class files for all services')
    
    args = parser.parse_args()
    
    # Check if CFR tool exists
    cfr_jar = "assets/jar/cfr-0.152.jar"
    if not os.path.exists(cfr_jar):
        logger.error(f"CFR tool does not exist: {cfr_jar}")
        sys.exit(1)
    
    decompiler = ClassDecompiler(args.database_url)
    
    try:
        if args.all_services:
            decompiler.decompile_classes_for_all_services()
        elif args.service_name:
            decompiler.decompile_classes_for_service(args.service_name, args.environment)
        else:
            logger.error("Must specify either --service-name or --all-services")
            sys.exit(1)
        
        logger.info("Class files decompilation completed successfully!")
        
    except Exception as e:
        logger.error(f"Class files decompilation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
