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

# Create database engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")

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
            JarFile.file_size,
            func.min(JarFile.last_modified).label('earliest_time'),
            func.max(JarFile.last_modified).label('latest_time'),
            func.count(JarFile.id).label('file_count'),
            func.count(func.distinct(JarFile.service_id)).label('service_count')
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
                file_count=row.file_count
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
            ClassFile.file_size,
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
async def get_jar_diff(jar_name: str, 
                      from_version: int = Query(..., description="源版本号"),
                      to_version: int = Query(..., description="目标版本号"),
                      file_path: Optional[str] = Query(None, description="特定文件路径")):
    """获取JAR文件版本差异"""
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
        
        # 构建文件映射
        from_files = {f.file_path: f for f in from_sources}
        to_files = {f.file_path: f for f in to_sources}
        
        # 计算差异
        file_changes = []
        file_diffs = []
        file_contents = {}
        
        all_files = set(from_files.keys()) | set(to_files.keys())
        
        for file_path in all_files:
            from_file = from_files.get(file_path)
            to_file = to_files.get(file_path)
            
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
                file_path=file_path,
                change_type=change_type,
                additions=additions,
                deletions=deletions,
                changes=changes,
                change_percentage=round(change_percentage, 1),
                size_before=from_file.file_size if from_file else 0,
                size_after=to_file.file_size if to_file else 0
            ))
            
            # 生成差异内容
            if from_file and to_file and from_file.file_content != to_file.file_content:
                hunks = generate_diff_hunks(from_file.file_content, to_file.file_content)
                file_diffs.append(FileDiff(
                    file_path=file_path,
                    hunks=hunks
                ))
            
            # 存储文件内容用于CodeMirror显示
            if file_path not in file_contents:
                file_contents[file_path] = {
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
        
        # 如果请求特定文件，返回该文件的内容
        if file_path and file_path in file_contents:
            return {
                "from_content": file_contents[file_path]["from_content"],
                "to_content": file_contents[file_path]["to_content"]
            }
        
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
    """生成Git风格的差异块"""
    from_lines = from_content.split('\n')
    to_lines = to_content.split('\n')
    
    # 使用difflib生成统一差异格式
    diff = list(difflib.unified_diff(from_lines, to_lines, lineterm=''))
    
    hunks = []
    current_hunk = None
    current_lines = []
    
    for line in diff:
        if line.startswith('@@'):
            # 新的差异块
            if current_hunk:
                current_hunk.lines = current_lines
                hunks.append(current_hunk)
            
            current_hunk = DiffHunk(header=line, lines=[])
            current_lines = []
        elif line.startswith('+') and not line.startswith('+++'):
            # 新增行
            current_lines.append(DiffLine(
                old_line=None,
                new_line=len(current_lines) + 1,
                type="added",
                content=line[1:]
            ))
        elif line.startswith('-') and not line.startswith('---'):
            # 删除行
            current_lines.append(DiffLine(
                old_line=len(current_lines) + 1,
                new_line=None,
                type="removed",
                content=line[1:]
            ))
        elif not line.startswith('+++') and not line.startswith('---'):
            # 上下文行
            current_lines.append(DiffLine(
                old_line=len(current_lines) + 1,
                new_line=len(current_lines) + 1,
                type="context",
                content=line[1:] if line.startswith(' ') else line
            ))
    
    # 添加最后一个差异块
    if current_hunk:
        current_hunk.lines = current_lines
        hunks.append(current_hunk)
    
    return hunks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
