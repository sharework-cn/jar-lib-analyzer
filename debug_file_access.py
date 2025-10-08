#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug file access issue - reproduce the problem where os.walk() finds files
but they cannot be accessed
"""

import os
import sys
from pathlib import Path

def get_long_path_prefix(path_str):
    """将普通路径转换为支持长路径的 UNC 格式路径。"""
    # 确保是绝对路径
    abs_path = os.path.abspath(path_str)
    # 检查是否已经是 UNC 格式或网络路径
    if abs_path.startswith('\\\\'):
        # 网络路径或 UNC 路径
        if abs_path.startswith('\\\\?\\'):
            return abs_path
        else:
            # 对于网络路径，使用 \\?\UNC\ 前缀
            unc_path = abs_path.replace('\\\\', '\\', 1) # 确保只有两个反斜杠开头
            return f"\\\\?\\UNC\\{unc_path[2:]}" # 移除开头的 \\ 并添加 \\?\UNC\
    else:
        # 本地路径，直接添加 \\?\ 前缀
        return f"\\\\?\\{abs_path}"

def debug_file_access():
    """Debug file access issue for specific directory"""
    
    # Target directory
    target_dir = r"work\prod\lib-decompile\tsm_core-card_supermarket_application_configuration-domain-1.0.0\20230425-dsop_core@local\com\justinmobile\card\supermarket\application\configuration\domain"
    
    # Target file
    target_file = "CardSupermarketConfigurationSort.java"
    
    print(f"=== Debug File Access Issue ===")
    print(f"Target directory: {target_dir}")
    print(f"Target file: {target_file}")
    print()
    
    # Check if directory exists
    print(f"1. Directory exists: {os.path.exists(target_dir)}")
    print(f"   Directory is dir: {os.path.isdir(target_dir)}")
    print()
    
    # List directory contents
    try:
        files = os.listdir(target_dir)
        print(f"2. Directory contents ({len(files)} files):")
        for file in files:
            print(f"   - {file}")
        print()
    except Exception as e:
        print(f"2. Error listing directory: {e}")
        print()
    
    # Walk through directory
    print("3. os.walk() results:")
    for root, dirs, files in os.walk(target_dir):
        print(f"   Root: {root}")
        print(f"   Files: {files}")
        if target_file in files:
            full_path = os.path.join(root, target_file)
            print(f"   *** Found target file at: {full_path} ***")
            print(f"   Full path exists: {os.path.exists(full_path)}")
            print(f"   Full path is file: {os.path.isfile(full_path)}")
        print()
    
    # Try to access the target file directly
    target_full_path = os.path.join(target_dir, target_file)
    print(f"4. Direct file access test:")
    print(f"   Target full path: {target_full_path}")
    print(f"   Path exists: {os.path.exists(target_full_path)}")
    print(f"   Path is file: {os.path.isfile(target_full_path)}")
    
    # Try different path formats
    path_variants = [
        target_full_path,
        target_full_path.replace('\\', '/'),
        os.path.normpath(target_full_path),
        os.path.abspath(target_full_path)
    ]
    
    print(f"5. Path format tests:")
    for i, path in enumerate(path_variants, 1):
        print(f"   {i}. {path}")
        print(f"      Exists: {os.path.exists(path)}")
        print(f"      Is file: {os.path.isfile(path)}")
        
        # Try to read file
        try:
            with open(path, 'r') as f:
                content = f.read(100)
            print(f"      Readable: Yes (first 100 chars: {content[:50]}...)")
        except Exception as e:
            print(f"      Readable: No (error: {e})")
        print()
    
    # Try to get file stats
    print(f"6. File stats test:")
    try:
        stat = os.stat(target_full_path)
        print(f"   File size: {stat.st_size} bytes")
        print(f"   Modified: {stat.st_mtime}")
    except Exception as e:
        print(f"   Stat error: {e}")
    
    # Test Windows long path support
    print(f"7. Windows long path support test:")
    try:
        long_path_prefixed = get_long_path_prefix(target_full_path)
        print(f"   Long path prefixed: {long_path_prefixed}")
        print(f"   Long path exists: {os.path.exists(long_path_prefixed)}")
        print(f"   Long path is file: {os.path.isfile(long_path_prefixed)}")
        
        # Try to read file with long path
        try:
            with open(long_path_prefixed, 'r', encoding='utf-8') as f:
                content = f.read(100)
            print(f"   Long path readable: Yes (first 100 chars: {content[:50]}...)")
        except Exception as e:
            print(f"   Long path readable: No (error: {e})")
    except Exception as e:
        print(f"   Long path error: {e}")
    
    print()
    print("=== End Debug ===")

if __name__ == "__main__":
    debug_file_access()
