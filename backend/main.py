# Source Code Difference Analysis System - Backend
# FastAPI-based web service

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, BigInteger, ForeignKey, func, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import hashlib
import difflib

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://jal:271828@172.30.80.95:32306/jal")

# Create database engine with connection pooling and error handling
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Test database connection
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("SELECT 1"))
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")
    print("Starting server without database connection...")
    engine = None
    SessionLocal = None

# Create FastAPI app
app = FastAPI(
    title="Java Library Analyzer API", 
    version="2.0.0",
    description="Java库分析系统 - 支持版本管理和差异分析"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/static", StaticFiles(directory=frontend_dist_path), name="static")
    print(f"Static files mounted from: {frontend_dist_path}")
else:
    print(f"Warning: Frontend dist directory not found: {frontend_dist_path}")

# Database models
Base = declarative_base()

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), index=True)
    environment = Column(String(50), default='production')
    ip_address = Column(String(15))
    port = Column(Integer)
    username = Column(String(50))
    password = Column(String(100))
    server_base_path = Column(String(500))
    jar_path = Column(String(500))
    classes_path = Column(String(500))
    source_path = Column(String(500))
    jar_info_file_path = Column(String(500))
    class_info_file_path = Column(String(500))
    jar_decompile_output_dir = Column(String(500))
    class_decompile_output_dir = Column(String(500))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jar_files = relationship("JarFile", back_populates="service")
    class_files = relationship("ClassFile", back_populates="service")

class JarFile(Base):
    __tablename__ = "jar_files"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    jar_name = Column(String(255))
    file_size = Column(BigInteger)
    last_modified = Column(DateTime)
    is_third_party = Column(Boolean, default=False)
    is_latest = Column(Boolean, default=False)
    file_path = Column(String(500))
    decompile_path = Column(String(500))
    version_no = Column(Integer)
    last_version_no = Column(Integer)
    source_hash = Column(String(64), index=True)  # Hash of all source files content
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service = relationship("Service", back_populates="jar_files")
    java_source_files = relationship("JavaSourceInJarFile", back_populates="jar_file")

class ClassFile(Base):
    __tablename__ = "class_files"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    class_full_name = Column(String(500))
    file_size = Column(BigInteger)
    last_modified = Column(DateTime)
    file_path = Column(String(500))
    decompile_path = Column(String(500))
    java_source_file_version_id = Column(Integer, ForeignKey("java_source_file_versions.id"), nullable=True)
    version_no = Column(Integer)
    last_version_no = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service = relationship("Service", back_populates="class_files")
    java_source_file_version = relationship("JavaSourceFileVersion", back_populates="class_files")

class JavaSourceFile(Base):
    __tablename__ = "java_source_files"
    
    id = Column(Integer, primary_key=True, index=True)
    class_full_name = Column(String(500), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    differences = relationship("SourceDifference", back_populates="java_source_file")
    versions = relationship("JavaSourceFileVersion", back_populates="java_source_file", cascade="all, delete-orphan")

class JavaSourceFileVersion(Base):
    __tablename__ = "java_source_file_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    java_source_file_id = Column(Integer, ForeignKey("java_source_files.id"))
    version = Column(String(50), index=True)
    file_path = Column(String(500))
    file_content = Column(Text)
    file_size = Column(BigInteger)
    last_modified = Column(DateTime, index=True)
    file_hash = Column(String(64), index=True)
    line_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    java_source_file = relationship("JavaSourceFile", back_populates="versions")
    class_files = relationship("ClassFile", back_populates="java_source_file_version")
    jar_files = relationship("JavaSourceInJarFile", back_populates="java_source_file_version")

class JavaSourceInJarFile(Base):
    __tablename__ = "java_source_in_jar_files"
    
    id = Column(Integer, primary_key=True, index=True)
    jar_file_id = Column(Integer, ForeignKey("jar_files.id"))
    java_source_file_version_id = Column(Integer, ForeignKey("java_source_file_versions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    jar_file = relationship("JarFile", back_populates="java_source_files")
    java_source_file_version = relationship("JavaSourceFileVersion", back_populates="jar_files")

class SourceDifference(Base):
    __tablename__ = "source_differences"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    java_source_file_id = Column(Integer, ForeignKey("java_source_files.id"))
    difference_type = Column(String(20))  # 'added', 'deleted', 'modified'
    line_number = Column(Integer)
    old_content = Column(Text)
    new_content = Column(Text)
    diff_context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship("Service")
    java_source_file = relationship("JavaSourceFile", back_populates="differences")

# Pydantic models for API
class ServiceResponse(BaseModel):
    id: int
    service_name: str
    ip_address: Optional[str]
    port: Optional[int]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class JavaSourceFileResponse(BaseModel):
    id: int
    class_full_name: str
    file_path: str
    file_size: Optional[int]
    last_modified: Optional[datetime]
    is_latest: bool
    line_count: Optional[int]
    
    class Config:
        from_attributes = True

class DifferenceResponse(BaseModel):
    id: int
    difference_type: str
    line_number: Optional[int]
    old_content: Optional[str]
    new_content: Optional[str]
    diff_context: Optional[str]
    
    class Config:
        from_attributes = True

# Dependency to get database session
def get_db():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not available")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Routes
@app.get("/")
async def root():
    return {"message": "Source Code Difference Analysis API", "version": "1.0.0"}

@app.get("/api/services", response_model=List[ServiceResponse])
async def get_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get list of services with pagination"""
    services = db.query(Service).offset(skip).limit(limit).all()
    return services

@app.get("/api/services/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get service details by ID"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@app.get("/api/services/{service_id}/java-classes", response_model=List[JavaSourceFileResponse])
async def get_service_java_classes(
    service_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get Java source files for a service"""
    java_files = db.query(JavaSourceFile).filter(
        JavaSourceFile.service_id == service_id
    ).offset(skip).limit(limit).all()
    return java_files

@app.get("/api/services/{service_id}/java-classes/{class_id}/differences", response_model=List[DifferenceResponse])
async def get_java_class_differences(
    service_id: int,
    class_id: int,
    db: Session = Depends(get_db)
):
    """Get differences for a specific Java class"""
    differences = db.query(SourceDifference).filter(
        SourceDifference.service_id == service_id,
        SourceDifference.java_source_file_id == class_id
    ).all()
    return differences

@app.get("/api/java-classes/{class_full_name}/latest")
async def get_latest_java_class(class_full_name: str, db: Session = Depends(get_db)):
    """Get the latest version of a Java class across all services"""
    latest_file = db.query(JavaSourceFile).filter(
        JavaSourceFile.class_full_name == class_full_name,
        JavaSourceFile.is_latest == True
    ).first()
    
    if not latest_file:
        raise HTTPException(status_code=404, detail="Latest version not found")
    
    return {
        "id": latest_file.id,
        "class_full_name": latest_file.class_full_name,
        "service_name": latest_file.service.service_name,
        "last_modified": latest_file.last_modified,
        "file_size": latest_file.file_size,
        "line_count": latest_file.line_count
    }

# Pydantic models for API
class SearchResult(BaseModel):
    jars: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]

class VersionInfo(BaseModel):
    version_no: int
    file_size: int
    earliest_time: str
    latest_time: str
    service_count: int
    services: List[str]
    file_count: int
    source_hash: Optional[str] = None  # 添加source_hash字段

class VersionHistory(BaseModel):
    item_name: str
    item_type: str
    versions: List[VersionInfo]

class FileChange(BaseModel):
    file_path: str
    change_type: str
    additions: int
    deletions: int
    changes: int
    change_percentage: float
    size_before: int
    size_after: int

class DiffSummary(BaseModel):
    total_files: int
    files_changed: int
    insertions: int
    deletions: int
    net_change: int

class DiffLine(BaseModel):
    old_line: Optional[int]
    new_line: Optional[int]
    type: str
    content: str

class DiffHunk(BaseModel):
    header: str
    lines: List[DiffLine]

class FileDiff(BaseModel):
    file_path: str
    hunks: List[DiffHunk]

class VersionDiff(BaseModel):
    from_version: int
    to_version: int
    file_changes: List[FileChange]
    summary: DiffSummary
    file_diffs: List[FileDiff]

# API Routes
@app.get("/api/search", response_model=SearchResult)
async def search_items(q: str = Query(..., description="搜索关键词"), 
                      type: str = Query("all", description="搜索类型: all, jar, class")):
    """搜索JAR文件和Class文件"""
    db = SessionLocal()
    try:
        results = {"jars": [], "classes": []}
        
        if type in ["all", "jar"]:
            # 搜索JAR文件
            jar_query = db.query(JarFile).filter(
                JarFile.jar_name.like(f"%{q}%"),
                JarFile.is_third_party == False
            )
            
            jar_groups = {}
            for jar in jar_query.all():
                if jar.jar_name not in jar_groups:
                    jar_groups[jar.jar_name] = {
                        "name": jar.jar_name,
                        "file_count": 0,
                        "version_count": 0,
                        "service_count": 0,
                        "services": set()
                    }
                
                jar_groups[jar.jar_name]["file_count"] += 1
                jar_groups[jar.jar_name]["services"].add(jar.service.service_name)
            
            # 获取版本统计
            for jar_name, data in jar_groups.items():
                version_count = db.query(func.count(func.distinct(JarFile.version_no))).filter(
                    JarFile.jar_name == jar_name,
                    JarFile.is_third_party == False
                ).scalar()
                
                data["version_count"] = version_count
                data["service_count"] = len(data["services"])
                data["services"] = list(data["services"])
                results["jars"].append(data)
        
        if type in ["all", "class"]:
            # 搜索Class文件
            class_query = db.query(ClassFile).filter(
                ClassFile.class_full_name.like(f"%{q}%")
            )
            
            class_groups = {}
            for cls in class_query.all():
                if cls.class_full_name not in class_groups:
                    class_groups[cls.class_full_name] = {
                        "name": cls.class_full_name,
                        "file_count": 0,
                        "version_count": 0,
                        "service_count": 0,
                        "services": set()
                    }
                
                class_groups[cls.class_full_name]["file_count"] += 1
                class_groups[cls.class_full_name]["services"].add(cls.service.service_name)
            
            # 获取版本统计
            for class_name, data in class_groups.items():
                version_count = db.query(func.count(func.distinct(ClassFile.version_no))).filter(
                    ClassFile.class_full_name == class_name
                ).scalar()
                
                data["version_count"] = version_count
                data["service_count"] = len(data["services"])
                data["services"] = list(data["services"])
                results["classes"].append(data)
        
        return results
        
    finally:
        db.close()

@app.get("/api/jars/{jar_name}/versions", response_model=VersionHistory)
async def get_jar_versions(jar_name: str):
    """获取JAR文件版本历史"""
    db = SessionLocal()
    try:
        # 获取JAR文件版本信息
        versions_query = db.query(
            JarFile.version_no,
            func.min(JarFile.file_size).label('file_size'),
            func.min(JarFile.last_modified).label('earliest_time'),
            func.max(JarFile.last_modified).label('latest_time'),
            func.count(JarFile.id).label('file_count'),
            func.count(func.distinct(JarFile.service_id)).label('service_count'),
            func.min(JarFile.source_hash).label('source_hash')  # 添加source_hash
        ).filter(
            JarFile.jar_name == jar_name,
            JarFile.is_third_party == False
        ).group_by(JarFile.version_no).order_by(JarFile.version_no)
        
        versions = []
        for row in versions_query.all():
            # 获取使用该版本的服务列表
            services = db.query(Service.service_name).join(JarFile).filter(
                JarFile.jar_name == jar_name,
                JarFile.version_no == row.version_no,
                JarFile.is_third_party == False
            ).distinct().all()
            
            versions.append(VersionInfo(
                version_no=row.version_no,
                file_size=row.file_size,
                earliest_time=row.earliest_time.isoformat(),
                latest_time=row.latest_time.isoformat(),
                service_count=row.service_count,
                services=[s.service_name for s in services],
                file_count=row.file_count,
                source_hash=row.source_hash  # 添加source_hash
            ))
        
        return VersionHistory(
            item_name=jar_name,
            item_type="jar",
            versions=versions
        )
        
    finally:
        db.close()

@app.get("/api/classes/{class_name}/versions", response_model=VersionHistory)
async def get_class_versions(class_name: str):
    """获取Class文件版本历史"""
    db = SessionLocal()
    try:
        # 获取Class文件版本信息
        versions_query = db.query(
            ClassFile.version_no,
            func.min(ClassFile.file_size).label('file_size'),
            func.min(ClassFile.last_modified).label('earliest_time'),
            func.max(ClassFile.last_modified).label('latest_time'),
            func.count(ClassFile.id).label('file_count'),
            func.count(func.distinct(ClassFile.service_id)).label('service_count')
        ).filter(
            ClassFile.class_full_name == class_name
        ).group_by(ClassFile.version_no).order_by(ClassFile.version_no)
        
        versions = []
        for row in versions_query.all():
            # 获取使用该版本的服务列表
            services = db.query(Service.service_name).join(ClassFile).filter(
                ClassFile.class_full_name == class_name,
                ClassFile.version_no == row.version_no
            ).distinct().all()
            
            versions.append(VersionInfo(
                version_no=row.version_no,
                file_size=row.file_size,
                earliest_time=row.earliest_time.isoformat(),
                latest_time=row.latest_time.isoformat(),
                service_count=row.service_count,
                services=[s.service_name for s in services],
                file_count=row.file_count
            ))
        
        return VersionHistory(
            item_name=class_name,
            item_type="class",
            versions=versions
        )
        
    finally:
        db.close()

@app.get("/api/jars/{jar_name}/diff")
async def get_jar_diff(
    jar_name: str,
    from_version: int = Query(..., description="源版本号"),
    to_version: int = Query(..., description="目标版本号"),
    file_path: Optional[str] = Query(None, description="特定文件路径"),
    resp_format: str = Query("structured", alias="format", description="返回格式: structured 或 unified"),
    include: str = Query("all", description="unified模式返回内容: diff|content|all")
):
    """获取JAR文件版本差异

    - structured: 保持原有结构化返回 (file_changes, file_diffs 等)
    - unified: 返回适配diff2html的单文件统一diff文本，置于 files[*].unified_diff
    """
    db = SessionLocal()
    try:
        # 获取两个版本的源码文件
        from_sources = db.query(JavaSourceFileVersion).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == from_version,
            JarFile.is_third_party == False
        ).all()
        
        to_sources = db.query(JavaSourceFileVersion).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == to_version,
            JarFile.is_third_party == False
        ).all()
        
        # 构建文件映射（按类名匹配，忽略服务器路径差异）
        def _extract_class_name(file_path: str) -> str:
            """从文件路径中提取类全名"""
            if not file_path:
                return file_path
            
            # 查找包名开始位置
            path_parts = file_path.replace('\\', '/').split('/')
            class_name = ""
            package_parts = []
            
            # 找到包名开始位置（com, org等）
            for i, part in enumerate(path_parts):
                if part in ['com', 'org', 'cn', 'net', 'io', 'java', 'javax']:
                    # 从包名开始到文件名前
                    package_parts = path_parts[i:-1]  # 排除文件名
                    if path_parts[-1].endswith('.java'):
                        class_name = path_parts[-1][:-5]  # 移除.java后缀
                    break
            
            if package_parts and class_name:
                return '.'.join(package_parts) + '.' + class_name
            elif class_name:
                return class_name
            else:
                return file_path  # 回退到原路径
        
        from_files = {_extract_class_name(f.file_path): f for f in from_sources}
        to_files = {_extract_class_name(f.file_path): f for f in to_sources}
        
        # 计算差异
        file_changes = []
        file_diffs = []
        file_contents = {}
        unified_files: List[Dict[str, Any]] = []
        
        all_files = set(from_files.keys()) | set(to_files.keys())
        
        for class_name in all_files:
            from_file = from_files.get(class_name)
            to_file = to_files.get(class_name)
            # 显示路径：将类名转换为相对路径格式
            display_path = class_name.replace('.', '/') + '.java'
            
            if not from_file and to_file:
                # 新增文件
                change_type = "added"
                additions = to_file.line_count or 0
                deletions = 0
            elif from_file and not to_file:
                # 删除文件
                change_type = "deleted"
                additions = 0
                deletions = from_file.line_count or 0
            elif from_file and to_file:
                # 修改文件
                change_type = "modified"
                from_content = from_file.file_content or ""
                to_content = to_file.file_content or ""
                
                # 计算行数差异
                from_lines = from_content.split('\n')
                to_lines = to_content.split('\n')
                
                diff = list(difflib.unified_diff(from_lines, to_lines, lineterm=''))
                additions = len([line for line in diff if line.startswith('+') and not line.startswith('+++')])
                deletions = len([line for line in diff if line.startswith('-') and not line.startswith('---')])
            else:
                continue
            
            changes = additions + deletions
            change_percentage = (changes / max(len(from_file.file_content.split('\n')) if from_file else 1, 1)) * 100
            
            file_changes.append(FileChange(
                file_path=display_path,
                change_type=change_type,
                additions=additions,
                deletions=deletions,
                changes=changes,
                change_percentage=round(change_percentage, 1),
                size_before=from_file.file_size if from_file else 0,
                size_after=to_file.file_size if to_file else 0
            ))
            
            # 生成差异内容
            if from_file and to_file:
                if from_file.file_content != to_file.file_content:
                    # 文件有差异
                    hunks = generate_diff_hunks(from_file.file_content, to_file.file_content)
                    file_diffs.append(FileDiff(
                        file_path=display_path,
                        hunks=hunks
                    ))

                    # 生成unified diff文本 (适配diff2html)
                    if resp_format == "unified":
                        from_lines = (from_file.file_content or "").split('\n')
                        to_lines = (to_file.file_content or "").split('\n')
                        # 为更好识别，补充 fromfile/tofile 以及文件头
                        unified_list = list(
                            difflib.unified_diff(
                                from_lines,
                                to_lines,
                                fromfile=f"a/{display_path}",
                                tofile=f"b/{display_path}",
                                lineterm=""
                            )
                        )
                        # 追加传统diff头，有助于diff2html识别多个文件
                        unified_text = []
                        unified_text.append(f"diff --git a/{display_path} b/{display_path}")
                        unified_text.append(f"--- a/{display_path}")
                        unified_text.append(f"+++ b/{display_path}")
                        # 过滤掉unified_list中重复的---和+++行
                        filtered_unified = [line for line in unified_list if not line.startswith('---') and not line.startswith('+++')]
                        unified_text.extend(filtered_unified)
                        unified_str = "\n".join(unified_text)
                        unified_files.append({
                            "file_path": display_path,
                            "change_type": change_type,
                            "additions": additions,
                            "deletions": deletions,
                            "unified_diff": unified_str,
                            "language": "java"
                        })
                else:
                    # 文件无差异，但仍要列出
                    if resp_format == "unified":
                        unified_files.append({
                            "file_path": display_path,
                            "change_type": "unchanged",
                            "additions": 0,
                            "deletions": 0,
                            "unified_diff": "",  # 无差异时不显示diff内容
                            "language": "java"
                        })
            elif (from_file and not to_file) and resp_format == "unified":
                # 文件被删除：生成只包含删除的diff（对比 /dev/null）
                from_lines = (from_file.file_content or "").split('\n')
                to_lines = []
                unified_list = list(
                    difflib.unified_diff(
                        from_lines,
                        to_lines,
                        fromfile=f"a/{display_path}",
                        tofile=f"b/{display_path}",
                        lineterm=""
                    )
                )
                unified_text = []
                unified_text.append(f"diff --git a/{display_path} b/{display_path}")
                unified_text.append(f"--- a/{display_path}")
                unified_text.append(f"+++ b/{display_path}")
                # 过滤掉unified_list中重复的---和+++行
                filtered_unified = [line for line in unified_list if not line.startswith('---') and not line.startswith('+++')]
                unified_text.extend(filtered_unified)
                unified_str = "\n".join(unified_text)
                unified_files.append({
                    "file_path": display_path,
                    "change_type": change_type,
                    "additions": 0,
                    "deletions": deletions,
                    "unified_diff": unified_str,
                    "language": "java"
                })
            elif (to_file and not from_file) and resp_format == "unified":
                # 新增文件：生成只包含新增的diff（对比 /dev/null）
                from_lines = []
                to_lines = (to_file.file_content or "").split('\n')
                unified_list = list(
                    difflib.unified_diff(
                        from_lines,
                        to_lines,
                        fromfile=f"a/{display_path}",
                        tofile=f"b/{display_path}",
                        lineterm=""
                    )
                )
                unified_text = []
                unified_text.append(f"diff --git a/{display_path} b/{display_path}")
                unified_text.append(f"--- a/{display_path}")
                unified_text.append(f"+++ b/{display_path}")
                # 过滤掉unified_list中重复的---和+++行
                filtered_unified = [line for line in unified_list if not line.startswith('---') and not line.startswith('+++')]
                unified_text.extend(filtered_unified)
                unified_str = "\n".join(unified_text)
                unified_files.append({
                    "file_path": display_path,
                    "change_type": change_type,
                    "additions": additions,
                    "deletions": 0,
                    "unified_diff": unified_str,
                    "language": "java"
                })
            
            # 存储文件内容用于CodeMirror显示
            if display_path not in file_contents:
                file_contents[display_path] = {
                    "from_content": from_file.file_content if from_file else "",
                    "to_content": to_file.file_content if to_file else ""
                }
        
        # 计算总统计
        total_insertions = sum(fc.additions for fc in file_changes)
        total_deletions = sum(fc.deletions for fc in file_changes)
        
        summary = DiffSummary(
            total_files=len(all_files),
            files_changed=len([fc for fc in file_changes if fc.change_type != "context"]),
            insertions=total_insertions,
            deletions=total_deletions,
            net_change=total_insertions - total_deletions
        )
        
        # 如果请求特定文件
        if file_path:
            if resp_format == "unified":
                # 返回该文件的unified diff
                f = next((f for f in unified_files if f["file_path"] == file_path), None)
                return f or {"file_path": file_path, "unified_diff": ""}
            else:
                if file_path in file_contents:
                    return {
                        "from_content": file_contents[file_path]["from_content"],
                        "to_content": file_contents[file_path]["to_content"]
                    }
                else:
                    return {
                        "from_content": "",
                        "to_content": ""
                    }
        
        if resp_format == "unified":
            # 统一diff返回结构
            return {
                "from_version": from_version,
                "to_version": to_version,
                "summary": summary.model_dump() if hasattr(summary, "model_dump") else summary.__dict__,
                "files": unified_files
            }
        else:
            return VersionDiff(
                from_version=from_version,
                to_version=to_version,
                file_changes=file_changes,
                summary=summary,
                file_diffs=file_diffs
            )
        
    finally:
        db.close()

def generate_diff_hunks(from_content: str, to_content: str) -> List[DiffHunk]:
    """生成GitHub风格的差异块"""
    from_lines = from_content.split('\n') if from_content else []
    to_lines = to_content.split('\n') if to_content else []
    
    # 使用difflib生成统一差异格式
    diff = list(difflib.unified_diff(from_lines, to_lines, lineterm=''))
    
    hunks = []
    current_hunk = None
    current_lines = []
    old_line_num = 0
    new_line_num = 0
    
    for line in diff:
        if line.startswith('@@'):
            # 新的差异块
            if current_hunk:
                current_hunk.lines = current_lines
                hunks.append(current_hunk)
            
            # 解析差异块头部信息
            import re
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 0
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 0
                
                # 生成更友好的差异块头部
                old_info = f"{old_start},{old_count}" if old_count > 0 else str(old_start)
                new_info = f"{new_start},{new_count}" if new_count > 0 else str(new_start)
                header = f"@@ -{old_info} +{new_info} @@"
                
                current_hunk = DiffHunk(header=header, lines=[])
                current_lines = []
                old_line_num = old_start
                new_line_num = new_start
        elif line.startswith('+') and not line.startswith('+++'):
            # 新增行
            current_lines.append(DiffLine(
                old_line=None,
                new_line=new_line_num,
                type="added",
                content=line[1:]
            ))
            new_line_num += 1
        elif line.startswith('-') and not line.startswith('---'):
            # 删除行
            current_lines.append(DiffLine(
                old_line=old_line_num,
                new_line=None,
                type="removed",
                content=line[1:]
            ))
            old_line_num += 1
        elif not line.startswith('+++') and not line.startswith('---') and line.strip():
            # 上下文行
            current_lines.append(DiffLine(
                old_line=old_line_num,
                new_line=new_line_num,
                type="context",
                content=line[1:] if line.startswith(' ') else line
            ))
            old_line_num += 1
            new_line_num += 1
    
    # 添加最后一个差异块
    if current_hunk:
        current_hunk.lines = current_lines
        hunks.append(current_hunk)
    
    return hunks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
