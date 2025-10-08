#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the setup and import process
"""

import os
import sys
import subprocess

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    try:
        from sqlalchemy import create_engine
        engine = create_engine("mysql+pymysql://jal:271828@172.30.80.95:32306/jal")
        connection = engine.connect()
        connection.close()
        print("[OK] Database connection successful")
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False

def test_data_files():
    """Test if required data files exist"""
    print("Testing data files...")
    
    files_to_check = [
        "../work/prod/server_info.csv",
        "../work/output/jar_analysis_report_20251007.csv",
        "../work/prod/lib-decompile",
        "../work/prod/classes-decompile"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"[OK] Found: {file_path}")
        else:
            print(f"[MISSING] Missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_import_script():
    """Test the import script"""
    print("Testing import script...")
    
    try:
        # Test with --stats-only to avoid actual import
        result = subprocess.run([
            sys.executable, "scripts/determine_latest_versions.py", "--stats-only"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("[OK] Import script test successful")
            return True
        else:
            print(f"[ERROR] Import script test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Import script test failed: {e}")
        return False

def main():
    print("=== Source Code Difference Analysis System - Setup Test ===\n")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Data Files", test_data_files),
        ("Import Script", test_import_script)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    print("\n=== Test Results ===")
    all_passed = True
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] All tests passed! System is ready for development.")
    else:
        print("\n[WARNING] Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
