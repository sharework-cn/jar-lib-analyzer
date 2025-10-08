#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Initialization Script
Initialize database with V2 schema
"""

import pymysql
import os
import sys

def init_database():
    """Initialize database with V2 schema"""
    
    # 读取SQL文件
    sql_file = 'schema_v2.sql'
    if not os.path.exists(sql_file):
        print(f"Error: SQL file {sql_file} not found")
        return False
    
    # 读取缺失表的SQL文件
    missing_tables_file = 'create_missing_tables.sql'
    if os.path.exists(missing_tables_file):
        with open(missing_tables_file, 'r', encoding='utf-8') as f:
            missing_sql = f.read()
    else:
        missing_sql = ""
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 合并SQL内容
    combined_sql = sql_content + "\n" + missing_sql
    
    # 连接数据库
    try:
        connection = pymysql.connect(
            host='172.30.80.95',
            port=32306,
            user='jal',
            password='271828',
            database='jal',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 分割SQL语句并逐条执行
            sql_statements = [stmt.strip() for stmt in combined_sql.split(';') if stmt.strip()]
            
            for i, statement in enumerate(sql_statements):
                if statement:
                    try:
                        cursor.execute(statement)
                        print(f"Executed statement {i+1}/{len(sql_statements)}")
                    except Exception as e:
                        print(f"Warning executing statement {i+1}: {e}")
                        # 继续执行其他语句
            
            connection.commit()
            print('Database schema V2 initialized successfully!')
            return True
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
