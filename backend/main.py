# Source Code Difference Analysis System - Backend
# FastAPI-based web service

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, BigInteger, ForeignKey, func, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import hashlib
import difflib
import math
import uuid
import re

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

class JarFileInfo(BaseModel):
    jar_name: str
    version_no: int
    last_version_no: Optional[int]
    file_size: Optional[int]
    last_modified: Optional[datetime]
    
    class Config:
        from_attributes = True

class ClassFileInfo(BaseModel):
    class_full_name: str
    version_no: int
    last_version_no: Optional[int]
    file_size: Optional[int]
    last_modified: Optional[datetime]
    
    class Config:
        from_attributes = True

class ServiceDetailResponse(BaseModel):
    id: int
    service_name: str
    ip_address: Optional[str]
    port: Optional[int]
    description: Optional[str]
    created_at: datetime
    last_updated: Optional[datetime]
    jar_files: List[JarFileInfo] = []
    class_files: List[ClassFileInfo] = []
    
    class Config:
        from_attributes = True

class ServiceListResponse(BaseModel):
    id: int
    service_name: str
    ip_address: Optional[str]
    port: Optional[int]
    description: Optional[str]
    created_at: datetime
    last_updated: Optional[datetime]
    jar_count: int = 0
    class_count: int = 0
    
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

@app.get("/api/services", response_model=List[ServiceListResponse])
async def get_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get list of services with pagination and statistics"""
    services = db.query(Service).offset(skip).limit(limit).all()
    
    service_responses = []
    for service in services:
        # Count JAR files
        jar_count = db.query(JarFile).filter(
            JarFile.service_id == service.id,
            JarFile.is_third_party == False
        ).distinct().count()
        
        # Count Class files (direct ClassFile records for this service)
        class_count = db.query(ClassFile).filter(
            ClassFile.service_id == service.id
        ).distinct().count()
        
        # Get last updated time
        jar_last_updated = db.query(JarFile.last_modified).filter(
            JarFile.service_id == service.id,
            JarFile.is_third_party == False
        ).order_by(JarFile.last_modified.desc()).first()
        
        class_last_updated = db.query(ClassFile.last_modified).filter(
            ClassFile.service_id == service.id
        ).order_by(ClassFile.last_modified.desc()).first()
        
        last_updated = None
        if jar_last_updated and class_last_updated:
            last_updated = max(jar_last_updated[0], class_last_updated[0])
        elif jar_last_updated:
            last_updated = jar_last_updated[0]
        elif class_last_updated:
            last_updated = class_last_updated[0]
        
        service_responses.append(ServiceListResponse(
            id=service.id,
            service_name=service.service_name,
            ip_address=service.ip_address,
            port=service.port,
            description=service.description,
            created_at=service.created_at,
            last_updated=last_updated,
            jar_count=jar_count,
            class_count=class_count
        ))
    
    return service_responses

@app.get("/api/services/{service_id}", response_model=ServiceDetailResponse)
async def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get service details by ID with JAR and Class files"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get JAR files for this service
    jar_files = db.query(JarFile).filter(
        JarFile.service_id == service_id,
        JarFile.is_third_party == False
    ).distinct().all()
    
    # Get Class files for this service (direct ClassFile records)
    class_files = db.query(ClassFile).filter(
        ClassFile.service_id == service_id
    ).distinct().all()
    
    # Convert to response format
    jar_file_infos = []
    for jar in jar_files:
        jar_file_infos.append(JarFileInfo(
            jar_name=jar.jar_name,
            version_no=jar.version_no,
            last_version_no=jar.last_version_no,
            file_size=jar.file_size,
            last_modified=jar.last_modified
        ))
    
    class_file_infos = []
    for class_file in class_files:
        # Handle None version
        version_no = 1
        if class_file.version_no:
            version_no = class_file.version_no
        
        last_version_no = 1
        if class_file.last_version_no:
            last_version_no = class_file.last_version_no
        
        class_file_infos.append(ClassFileInfo(
            class_full_name=class_file.class_full_name,
            version_no=version_no,
            last_version_no=last_version_no,
            file_size=class_file.file_size,
            last_modified=class_file.last_modified
        ))
    
    # Sort by name
    jar_file_infos.sort(key=lambda x: x.jar_name)
    class_file_infos.sort(key=lambda x: x.class_full_name)
    
    return ServiceDetailResponse(
        id=service.id,
        service_name=service.service_name,
        ip_address=service.ip_address,
        port=service.port,
        description=service.description,
        created_at=service.created_at,
        last_updated=max([jar.last_modified for jar in jar_files] + [cls.last_modified for cls in class_files], default=None),
        jar_files=jar_file_infos,
        class_files=class_file_infos
    )

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
    jar_sources: List[Dict[str, Any]]

class ServiceInfo(BaseModel):
    id: int
    name: str

class VersionInfo(BaseModel):
    version_no: int
    file_size: int
    earliest_time: str
    latest_time: str
    service_count: int
    services: List[ServiceInfo]
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
    class_full_name: Optional[str] = None

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
async def search_items(q: str = Query(..., description="Search keyword"), 
                      type: str = Query("all", description="Search type: all, jar, class, jar-source")):
    """Search JAR files, Class files, and JAR SOURCE files"""
    db = SessionLocal()
    try:
        results = {"jars": [], "classes": [], "jar_sources": []}
        
        if type in ["all", "jar"]:
            # Search JAR files
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
            
            # Get version statistics
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
            # Search Class files
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
            
            # Get version statistics
            for class_name, data in class_groups.items():
                version_count = db.query(func.count(func.distinct(ClassFile.version_no))).filter(
                    ClassFile.class_full_name == class_name
                ).scalar()
                
                data["version_count"] = version_count
                data["service_count"] = len(data["services"])
                data["services"] = list(data["services"])
                results["classes"].append(data)
        
        if type in ["all", "jar-source"]:
            # Search JAR SOURCE files (Java source files in JAR files)
            # Join with JavaSourceFile to search by class_full_name
            jar_source_query = db.query(JavaSourceFileVersion).join(JavaSourceFile).join(JavaSourceInJarFile).join(JarFile).filter(
                JavaSourceFile.class_full_name.like(f"%{q}%"),
                JarFile.is_third_party == False
            )
            
            jar_source_groups = {}
            for source in jar_source_query.all():
                class_name = source.java_source_file.class_full_name
                file_path = source.file_path
                
                # Get JAR file info through the relationship
                jar_file = None
                service_name = None
                for jar_rel in source.jar_files:
                    jar_file = jar_rel.jar_file
                    service_name = jar_file.service.service_name
                    break  # Take the first one
                
                if not jar_file:
                    continue
                
                if class_name not in jar_source_groups:
                    jar_source_groups[class_name] = {
                        "name": class_name,
                        "file_path": file_path,
                        "jar_name": jar_file.jar_name,
                        "file_count": 0,
                        "version_count": 0,
                        "service_count": 0,
                        "services": set()
                    }
                
                jar_source_groups[class_name]["file_count"] += 1
                jar_source_groups[class_name]["services"].add(service_name)
            
            # Get version statistics
            for class_name, data in jar_source_groups.items():
                version_count = db.query(func.count(func.distinct(JavaSourceFileVersion.version))).join(JavaSourceFile).join(JavaSourceInJarFile).join(JarFile).filter(
                    JavaSourceFile.class_full_name == class_name,
                    JarFile.is_third_party == False
                ).scalar()
                
                data["version_count"] = version_count
                data["service_count"] = len(data["services"])
                data["services"] = list(data["services"])
                results["jar_sources"].append(data)
        
        return results
        
    finally:
        db.close()

@app.get("/api/jars/{jar_name}/sources/{version_no}")
async def get_jar_source_files(jar_name: str, version_no: int, db: Session = Depends(get_db)):
    """Get JAR source files for a specific version"""
    # First get the JAR file to get its last_modified time
    jar_file = db.query(JarFile).filter(
        JarFile.jar_name == jar_name,
        JarFile.version_no == version_no,
        JarFile.is_third_party == False
    ).first()
    
    if not jar_file:
        raise HTTPException(status_code=404, detail="JAR file not found")
    
    # Get source files
    source_files = db.query(JavaSourceFileVersion).join(JavaSourceInJarFile).join(JarFile).options(
        joinedload(JavaSourceFileVersion.java_source_file)
    ).filter(
        JarFile.jar_name == jar_name,
        JarFile.version_no == version_no,
        JarFile.is_third_party == False
    ).all()
    
    # Add JAR last_modified time to each source file
    result = []
    for source_file in source_files:
        source_file_dict = {
            "java_source_file": source_file.java_source_file,
            "file_path": source_file.file_path,
            "file_size": source_file.file_size,
            "line_count": source_file.line_count,
            "last_modified": jar_file.last_modified.isoformat() if jar_file.last_modified else None,  # Use JAR's last_modified
            "version": source_file.version,
            "file_content": source_file.file_content
        }
        result.append(source_file_dict)
    
    return result

@app.get("/api/jars/{jar_name}/sources/{version_no}/content")
async def get_jar_source_file_content(
    jar_name: str, 
    version_no: int, 
    file_path: str = Query(..., description="File path"),
    db: Session = Depends(get_db)
):
    """Get specific JAR source file content"""
    # 首先尝试通过file_path精确匹配
    source_file = db.query(JavaSourceFileVersion).join(JavaSourceInJarFile).join(JarFile).filter(
        JarFile.jar_name == jar_name,
        JarFile.version_no == version_no,
        JavaSourceFileVersion.file_path == file_path,
        JarFile.is_third_party == False
    ).first()
    
    # 如果精确匹配失败，尝试通过类名匹配
    if not source_file:
        # 从file_path中提取类名（去掉.java后缀，将/替换为.）
        class_name = file_path.replace('.java', '').replace('/', '.')
        
        source_file = db.query(JavaSourceFileVersion).join(JavaSourceInJarFile).join(JarFile).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == version_no,
            JavaSourceFile.class_full_name == class_name,
            JarFile.is_third_party == False
        ).first()
    
    if not source_file:
        raise HTTPException(status_code=404, detail="Source file not found")
    
    return {"content": source_file.file_content or ""}

@app.get("/api/classes/{class_name}/sources/{version_no}/content")
async def get_class_source_file_content(
    class_name: str, 
    version_no: int, 
    class_full_name: str = Query(..., description="Class full name"),
    db: Session = Depends(get_db)
):
    """Get specific Class source file content"""
    # 通过Class文件找到对应的Java源码文件版本
    class_file = db.query(ClassFile).filter(
        ClassFile.class_full_name == class_name,
        ClassFile.version_no == version_no
    ).first()
    
    if not class_file or not class_file.java_source_file_version_id:
        raise HTTPException(status_code=404, detail="Class file or source not found")
    
    # 获取Java源码文件版本
    source_file = db.query(JavaSourceFileVersion).filter(
        JavaSourceFileVersion.id == class_file.java_source_file_version_id
    ).first()
    
    if not source_file:
        raise HTTPException(status_code=404, detail="Source file not found")
    
    return {"content": source_file.file_content or ""}

# New API endpoints for JARs and Java Sources
@app.get("/api/jars")
async def get_jars(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    last_jar_name: str = Query(None, description="Last jar name from previous page for cursor-based pagination"),
    db: Session = Depends(get_db)
):
    """Get list of all JAR files with statistics and cursor-based pagination"""
    # Build base query to get JAR names and basic stats
    base_query = db.query(
        JarFile.jar_name,
        func.min(JarFile.last_modified).label('earliest_modified'),
        func.max(JarFile.last_modified).label('latest_modified')
    ).filter(
        JarFile.is_third_party == False
    ).group_by(JarFile.jar_name)
    
    # Apply cursor-based pagination
    if last_jar_name:
        base_query = base_query.filter(JarFile.jar_name > last_jar_name)
    
    # Get data with limit + 1 to check if there are more pages
    jar_stats = base_query.order_by(JarFile.jar_name).limit(limit + 1).all()
    
    # Check if there are more pages
    has_more = len(jar_stats) > limit
    if has_more:
        jar_stats = jar_stats[:limit]  # Remove the extra record
    
    result = []
    for stat in jar_stats:
        jar_name = stat.jar_name
        
        # Count distinct versions for this JAR
        version_count = db.query(func.count(func.distinct(JarFile.version_no))).filter(
            JarFile.jar_name == jar_name,
            JarFile.is_third_party == False
        ).scalar()
        
        # Count distinct services using this JAR
        service_count = db.query(func.count(func.distinct(JarFile.service_id))).filter(
            JarFile.jar_name == jar_name,
            JarFile.is_third_party == False
        ).scalar()
        
        result.append({
            "jar_name": jar_name,
            "version_count": version_count,
            "service_count": service_count,
            "earliest_modified": stat.earliest_modified.isoformat() if stat.earliest_modified else None,
            "latest_modified": stat.latest_modified.isoformat() if stat.latest_modified else None
        })
    
    return {
        "data": result,
        "has_more": has_more,
        "last_jar_name": result[-1]["jar_name"] if result else None,
        "limit": limit
    }

@app.get("/api/java-sources")
async def get_java_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    last_class_name: str = Query(None, description="Last class name from previous page for cursor-based pagination"),
    db: Session = Depends(get_db)
):
    """Get list of all Java source files with source information and cursor-based pagination"""
    # Build base query
    base_query = db.query(
        JavaSourceFile.class_full_name,
        func.count(JavaSourceFile.id).label('version_count')
    ).group_by(JavaSourceFile.class_full_name)
    
    # Apply cursor-based pagination
    if last_class_name:
        base_query = base_query.filter(JavaSourceFile.class_full_name > last_class_name)
    
    # Get data with limit + 1 to check if there are more pages
    source_stats = base_query.order_by(JavaSourceFile.class_full_name).limit(limit + 1).all()
    
    # Check if there are more pages
    has_more = len(source_stats) > limit
    if has_more:
        source_stats = source_stats[:limit]  # Remove the extra record
    
    result = []
    for stat in source_stats:
        # Check if this source is in JAR files
        jar_count = db.query(JavaSourceInJarFile).join(
            JavaSourceFileVersion, JavaSourceInJarFile.java_source_file_version_id == JavaSourceFileVersion.id
        ).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).filter(
            JavaSourceFile.class_full_name == stat.class_full_name
        ).count()
        
        # Check if this source is in Class files
        class_count = db.query(ClassFile).join(
            JavaSourceFileVersion, ClassFile.java_source_file_version_id == JavaSourceFileVersion.id
        ).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).filter(
            JavaSourceFile.class_full_name == stat.class_full_name
        ).count()
        
        # Determine source type
        source_types = []
        if jar_count > 0:
            source_types.append("JAR")
        if class_count > 0:
            source_types.append("Class")
        
        result.append({
            "class_full_name": stat.class_full_name,
            "version_count": stat.version_count,
            "source_types": source_types,
            "jar_count": jar_count,
            "class_count": class_count
        })
    
    return {
        "data": result,
        "has_more": has_more,
        "last_class_name": result[-1]["class_full_name"] if result else None,
        "limit": limit
    }

# Critical differences analysis API
@app.get("/api/services/{service_id}/critical-differences")
async def get_service_critical_differences(service_id: int, db: Session = Depends(get_db)):
    """Get critical compatibility differences for a service"""
    # Get service
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get JAR files for this service
    jar_files = db.query(JarFile).filter(
        JarFile.service_id == service_id,
        JarFile.is_third_party == False
    ).all()
    
    # Get Class files for this service
    class_files = db.query(ClassFile).filter(
        ClassFile.service_id == service_id
    ).all()
    
    all_critical_changes = []
    
    # Analyze JAR differences
    for jar in jar_files:
        latest_version = db.query(func.max(JarFile.version_no)).filter(
            JarFile.jar_name == jar.jar_name,
            JarFile.is_third_party == False
        ).scalar()
        
        if jar.version_no != latest_version:
            try:
                diff_content = get_jar_diff_content(jar.jar_name, jar.version_no, latest_version, db)
                # Extract critical changes from diff content (simplified for API)
                all_critical_changes.append({
                    'type': 'jar_differences',
                    'jar_name': jar.jar_name,
                    'current_version': jar.version_no,
                    'latest_version': latest_version,
                    'has_critical_changes': 'Critical Compatibility Issues' in diff_content
                })
            except Exception as e:
                all_critical_changes.append({
                    'type': 'jar_differences',
                    'jar_name': jar.jar_name,
                    'current_version': jar.version_no,
                    'latest_version': latest_version,
                    'error': str(e)
                })
    
    # Analyze Class differences
    for class_file in class_files:
        latest_version = db.query(func.max(ClassFile.version_no)).filter(
            ClassFile.class_full_name == class_file.class_full_name
        ).scalar()
        
        if class_file.version_no != latest_version:
            try:
                diff_content = get_class_diff_content(class_file.class_full_name, class_file.version_no, latest_version, db)
                all_critical_changes.append({
                    'type': 'class_differences',
                    'class_name': class_file.class_full_name,
                    'current_version': class_file.version_no,
                    'latest_version': latest_version,
                    'has_critical_changes': 'Critical Compatibility Issues' in diff_content
                })
            except Exception as e:
                all_critical_changes.append({
                    'type': 'class_differences',
                    'class_name': class_file.class_full_name,
                    'current_version': class_file.version_no,
                    'latest_version': latest_version,
                    'error': str(e)
                })
    
    return {
        "service_id": service_id,
        "service_name": service.service_name,
        "critical_changes": all_critical_changes,
        "total_items": len(jar_files) + len(class_files),
        "items_with_differences": len(all_critical_changes)
    }

# Export APIs
@app.get("/api/services/{service_id}/export")
async def export_service_details(service_id: int, db: Session = Depends(get_db)):
    """Export service details as Markdown"""
    # Get service details
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get JAR files
    jar_files = db.query(JarFile).filter(
        JarFile.service_id == service_id,
        JarFile.is_third_party == False
    ).all()
    
    # Get Class files
    class_files = db.query(ClassFile).filter(
        ClassFile.service_id == service_id
    ).all()
    
    # Generate Markdown content
    markdown_content = generate_service_export_markdown(service, jar_files, class_files, db)
    
    return {
        "filename": f"service_{service.service_name}_{service_id}_export.md",
        "content": markdown_content,
        "content_type": "text/markdown"
    }

@app.get("/api/jars/{jar_name}/export")
async def export_jar_history(jar_name: str, db: Session = Depends(get_db)):
    """Export JAR version history as Markdown"""
    # Get all versions of the JAR
    versions = db.query(JarFile).filter(
        JarFile.jar_name == jar_name,
        JarFile.is_third_party == False
    ).order_by(JarFile.version_no).all()
    
    if not versions:
        raise HTTPException(status_code=404, detail="JAR not found")
    
    # Generate Markdown content
    markdown_content = generate_jar_export_markdown(jar_name, versions, db)
    
    return {
        "filename": f"jar_{jar_name.replace('.jar', '')}_history_export.md",
        "content": markdown_content,
        "content_type": "text/markdown"
    }

def generate_service_export_markdown(service, jar_files, class_files, db):
    """Generate Markdown content for service export"""
    content = []
    
    # Service header
    content.append(f"# Service: {service.service_name}")
    content.append("")
    content.append(f"**Service ID:** {service.id}")
    content.append(f"**IP Address:** {service.ip_address}")
    content.append(f"**Port:** {service.port}")
    content.append(f"**Description:** {service.description or 'N/A'}")
    content.append(f"**Created At:** {service.created_at}")
    content.append("")
    
    # JAR Files section
    content.append("## JAR Files")
    content.append("")
    content.append(f"Total JAR files: {len(jar_files)}")
    content.append("")
    
    # Create JAR files table
    content.append("| JAR Name | Version | Status | File Size | Last Modified |")
    content.append("|----------|---------|--------|-----------|---------------|")
    
    jar_differences = []
    all_critical_changes = []  # Collect all critical changes
    
    for jar in jar_files:
        # Check if not latest version
        latest_version = db.query(func.max(JarFile.version_no)).filter(
            JarFile.jar_name == jar.jar_name,
            JarFile.is_third_party == False
        ).scalar()
        
        if jar.version_no != latest_version:
            status = f"⚠️ Not Latest (Latest: {latest_version})"
            # Generate unique anchor ID
            jar_anchor_id = str(uuid.uuid4()).replace('-', '')[:16]
            jar_differences.append({
                'jar_name': jar.jar_name,
                'current_version': jar.version_no,
                'latest_version': latest_version,
                'type': 'jar',
                'anchor_id': jar_anchor_id
            })
            status = f"⚠️ Not Latest (Latest: {latest_version}) - [View Differences](#{jar_anchor_id})"
        else:
            status = "✅ Latest Version"
        
        content.append(f"| {jar.jar_name} | {jar.version_no} | {status} | {format_file_size(jar.file_size)} | {jar.last_modified} |")
    
    content.append("")
    
    # Class Files section
    content.append("## Class Files")
    content.append("")
    content.append(f"Total Class files: {len(class_files)}")
    content.append("")
    
    # Create Class files table
    content.append("| Class Name | Version | Status | File Size | Last Modified |")
    content.append("|------------|---------|--------|-----------|---------------|")
    
    class_differences = []
    for class_file in class_files:
        # Check if not latest version
        latest_version = db.query(func.max(ClassFile.version_no)).filter(
            ClassFile.class_full_name == class_file.class_full_name
        ).scalar()
        
        if class_file.version_no != latest_version:
            status = f"⚠️ Not Latest (Latest: {latest_version})"
            # Generate unique anchor ID
            class_anchor_id = str(uuid.uuid4()).replace('-', '')[:16]
            class_differences.append({
                'class_name': class_file.class_full_name,
                'current_version': class_file.version_no,
                'latest_version': latest_version,
                'type': 'class',
                'anchor_id': class_anchor_id
            })
            status = f"⚠️ Not Latest (Latest: {latest_version}) - [View Differences](#{class_anchor_id})"
        else:
            status = "✅ Latest Version"
        
        content.append(f"| {class_file.class_full_name} | {class_file.version_no} | {status} | {format_file_size(class_file.file_size)} | {class_file.last_modified} |")
    
    content.append("")
    
    # Differences section
    if jar_differences or class_differences:
        content.append("## Differences from Latest Versions")
        content.append("")
        
        # JAR differences
        for i, diff in enumerate(jar_differences):
            content.append(f'<a id="{diff["anchor_id"]}"/>')
            content.append(f"### {diff['jar_name']} (Version {diff['current_version']} → {diff['latest_version']})")
            content.append("")
            
            try:
                diff_content = get_jar_diff_content(diff['jar_name'], diff['current_version'], diff['latest_version'], db)
                if diff_content and diff_content != "No differences found between versions":
                    content.append(diff_content)
                    
                    # Analyze critical changes for this JAR
                    jar_critical_changes = analyze_jar_critical_changes(diff['jar_name'], diff['current_version'], diff['latest_version'], db)
                    all_critical_changes.extend(jar_critical_changes)
                else:
                    content.append("*No differences found*")
            except Exception as e:
                content.append(f"*Error generating diff: {str(e)}*")
            
            content.append("")
        
        # Class differences
        for i, diff in enumerate(class_differences):
            content.append(f'<a id="{diff["anchor_id"]}"/>')
            content.append(f"### {diff['class_name']} (Version {diff['current_version']} → {diff['latest_version']})")
            content.append("")
            
            try:
                diff_content = get_class_diff_content(diff['class_name'], diff['current_version'], diff['latest_version'], db)
                if diff_content and diff_content != "No differences found between versions":
                    content.append(diff_content)
                    
                    # Analyze critical changes for this Class
                    class_critical_changes = analyze_class_critical_changes(diff['class_name'], diff['current_version'], diff['latest_version'], db)
                    all_critical_changes.extend(class_critical_changes)
                else:
                    content.append("*No differences found*")
            except Exception as e:
                content.append(f"*Error generating diff: {str(e)}*")
            
            content.append("")
    
    # Critical Changes Summary section (at the end)
    if all_critical_changes:
        content.append("## ⚠️ Critical Compatibility Issues Summary")
        content.append("")
        content.append("The following changes may cause compatibility issues during incremental deployment:")
        content.append("")
        
        # Group changes by type and remove duplicates
        processed_changes = []
        removed_classes = set()
        
        for change in all_critical_changes:
            # Extract class name from location for class removal tracking
            if 'JAR:' in change['location'] and '→ Class:' in change['location']:
                class_name = change['location'].split('→ Class: ')[1].split(' (')[0]
                class_short_name = class_name.split('.')[-1]
                
                if change['type'] == 'removed_class':
                    removed_classes.add(class_short_name)
                    processed_changes.append(change)
                elif change['type'] in ['removed_method', 'modified_method_signature']:
                    # Only add method changes if the class wasn't removed
                    if class_short_name not in removed_classes:
                        processed_changes.append(change)
            else:
                # Direct class changes
                if change['type'] == 'removed_class':
                    class_name = change['location'].split('Class: ')[1].split(' (')[0]
                    class_short_name = class_name.split('.')[-1]
                    removed_classes.add(class_short_name)
                processed_changes.append(change)
        
        for change in processed_changes:
            severity_icon = "🔴" if change['severity'] == 'high' else "🟡"
            
            # Generate simplified title
            if change['type'] == 'removed_class':
                class_name = change['description'].split("'")[1]
                class_short_name = class_name.split('.')[-1]
                title = f"Class Removed: {class_short_name}"
            elif change['type'] == 'removed_method':
                method_name = change['description'].split("'")[1].split('(')[0]
                title = f"Method Removed: {method_name}"
            elif change['type'] == 'modified_method_signature':
                method_name = change['description'].split("'")[1]
                title = f"Method Modified: {method_name}"
            else:
                title = change['type'].replace('_', ' ').title()
            
            content.append(f"### {severity_icon} {title}")
            content.append("")
            content.append(f"**Location:** {change['location']}")
            content.append("")
            content.append(f"**Issue:** {change['description']}")
            content.append("")
            
            if 'details' in change:
                content.append("**Details:**")
                content.append("```diff")
                content.append(change['details'])
                content.append("```")
                content.append("")
    
    return "\n".join(content)

def generate_jar_export_markdown(jar_name, versions, db):
    """Generate Markdown content for JAR export"""
    content = []
    
    # JAR header
    content.append(f"# JAR: {jar_name}")
    content.append("")
    content.append(f"Total versions: {len(versions)}")
    content.append("")
    
    # Version history
    content.append("## Version History")
    content.append("")
    
    for i, version in enumerate(versions):
        content.append(f"### Version {version.version_no}")
        content.append("")
        content.append(f"- **File Size:** {format_file_size(version.file_size)}")
        content.append(f"- **Last Modified:** {version.last_modified}")
        
        # Get services using this version
        services = db.query(Service).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == version.version_no,
            JarFile.is_third_party == False
        ).all()
        
        content.append(f"- **Used by Services:** {len(services)}")
        if services:
            service_names = [s.service_name for s in services]
            content.append(f"  - {', '.join(service_names)}")
        
        content.append("")
        
        # Show differences from previous version
        if i > 0:
            prev_version = versions[i-1]
            content.append(f"#### Changes from Version {prev_version.version_no}")
            content.append("")
            
            try:
                diff_content = get_jar_diff_content(jar_name, prev_version.version_no, version.version_no, db)
                if diff_content and diff_content != "No differences found between versions":
                    content.append(diff_content)
                else:
                    content.append("*No differences found*")
            except Exception as e:
                content.append(f"*Error generating diff: {str(e)}*")
            
            content.append("")
    
    return "\n".join(content)

def analyze_jar_critical_changes(jar_name, from_version, to_version, db):
    """Analyze critical changes for a JAR between two versions"""
    try:
        # Get source files for both versions
        from_sources = db.query(JavaSourceFileVersion, JavaSourceFile.class_full_name).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == from_version,
            JarFile.is_third_party == False
        ).all()
        
        to_sources = db.query(JavaSourceFileVersion, JavaSourceFile.class_full_name).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == to_version,
            JarFile.is_third_party == False
        ).all()
        
        # Create file mapping
        from_files = {class_name: sf.file_content for sf, class_name in from_sources}
        to_files = {class_name: sf.file_content for sf, class_name in to_sources}
        
        all_critical_changes = []
        
        # Analyze each class
        all_classes = set(from_files.keys()) | set(to_files.keys())
        for class_name in all_classes:
            from_content = from_files.get(class_name, "")
            to_content = to_files.get(class_name, "")
            
            if from_content != to_content:
                context_info = f"JAR: {jar_name} → Class: {class_name} (v{from_version} → v{to_version})"
                critical_changes = analyze_critical_differences(from_content, to_content, context_info)
                all_critical_changes.extend(critical_changes)
        
        return all_critical_changes
    except Exception as e:
        return []

def analyze_class_critical_changes(class_name, from_version, to_version, db):
    """Analyze critical changes for a Class between two versions"""
    try:
        # Get source content for both versions
        from_source = db.query(JavaSourceFileVersion).join(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == from_version
        ).first()
        
        to_source = db.query(JavaSourceFileVersion).join(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == to_version
        ).first()
        
        if not from_source or not to_source:
            return []
        
        from_content = from_source.file_content or ""
        to_content = to_source.file_content or ""
        
        context_info = f"Class: {class_name} (v{from_version} → v{to_version})"
        return analyze_critical_differences(from_content, to_content, context_info)
    except Exception as e:
        return []

def extract_critical_changes_from_diff(diff_content, location_name, location_type):
    """Extract critical changes from diff content with proper context"""
    critical_changes = []
    
    if "Critical Compatibility Issues" not in diff_content:
        return critical_changes
    
    # Parse the diff content to extract critical changes
    lines = diff_content.split('\n')
    in_critical_section = False
    current_change = None
    
    for line in lines:
        if "## ⚠️ Critical Compatibility Issues" in line:
            in_critical_section = True
            continue
        
        if in_critical_section:
            if line.startswith("### 🔴") or line.startswith("### 🟡"):
                # Save previous change if exists
                if current_change:
                    critical_changes.append(current_change)
                
                # Start new change
                severity = "high" if "🔴" in line else "medium"
                change_type = line.split("🔴")[-1].split("🟡")[-1].strip()
                current_change = {
                    'type': change_type.lower().replace(' ', '_'),
                    'severity': severity,
                    'location': f"{location_type}: {location_name}",
                    'description': '',
                    'details': ''
                }
            elif current_change and line.startswith("**Issue:**"):
                current_change['description'] = line.replace("**Issue:**", "").strip()
            elif current_change and line.startswith("```diff"):
                # Start collecting details
                current_change['details'] = ""
            elif current_change and current_change['details'] != "" and not line.startswith("```"):
                # Collect details
                current_change['details'] += line + "\n"
            elif current_change and line.startswith("```") and current_change['details'] != "":
                # End of details
                current_change['details'] = current_change['details'].strip()
    
    # Add the last change
    if current_change:
        critical_changes.append(current_change)
    
    return critical_changes

def get_jar_diff_content(jar_name, from_version, to_version, db):
    """Get diff content between two JAR versions - only show files with differences"""
    try:
        # Get source files for both versions with class names
        from_sources = db.query(JavaSourceFileVersion, JavaSourceFile.class_full_name).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == from_version,
            JarFile.is_third_party == False
        ).all()
        
        to_sources = db.query(JavaSourceFileVersion, JavaSourceFile.class_full_name).join(
            JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
        ).join(JavaSourceInJarFile).join(JarFile).filter(
            JarFile.jar_name == jar_name,
            JarFile.version_no == to_version,
            JarFile.is_third_party == False
        ).all()
        
        # Create file mapping using class_full_name
        from_files = {class_name: sf.file_content for sf, class_name in from_sources}
        to_files = {class_name: sf.file_content for sf, class_name in to_sources}
        
        # Generate unified diff - only for files with differences
        diff_lines = []
        all_files = set(from_files.keys()) | set(to_files.keys())
        
        files_with_differences = []
        
        for class_name in sorted(all_files):
            from_content = from_files.get(class_name, "")
            to_content = to_files.get(class_name, "")
            
            # Only process files that actually have differences
            if from_content != to_content:
                files_with_differences.append(class_name)
                
                # Add file header with HTML anchor
                class_anchor_id = str(uuid.uuid4()).replace('-', '')[:16]
                diff_lines.append(f'<a id="{class_anchor_id}"/>')
                diff_lines.append(f"#### {class_name}")
                diff_lines.append("")
                
                # Generate diff using difflib
                from_lines = from_content.splitlines(keepends=True) if from_content else []
                to_lines = to_content.splitlines(keepends=True) if to_content else []
                
                diff = difflib.unified_diff(
                    from_lines,
                    to_lines,
                    fromfile=f"v{from_version}",
                    tofile=f"v{to_version}",
                    lineterm=""
                )
                
                # Add diff content
                diff_lines.append("```diff")
                diff_content = list(diff)[2:]  # Skip file headers
                if diff_content:
                    # Remove empty lines between diff lines and fix line endings
                    filtered_content = []
                    for line in diff_content:
                        if line.strip() or line.startswith(('@@', '---', '+++')):
                            # Remove trailing newlines to prevent double spacing
                            filtered_content.append(line.rstrip('\n'))
                    diff_lines.extend(filtered_content)
                else:
                    diff_lines.append("No differences found")
                diff_lines.append("```")
                diff_lines.append("")
        
        if not files_with_differences:
            return "No differences found between versions"
        
        # Add summary
        summary = f"**Classes with differences:** {len(files_with_differences)}\n"
        summary += f"**Changed classes:** {', '.join(files_with_differences)}\n\n"
        
        return summary + "\n".join(diff_lines)
    except Exception as e:
        return f"Error generating diff: {str(e)}"

def get_class_diff_content(class_name, from_version, to_version, db):
    """Get diff content between two class versions - only show differences"""
    try:
        # Get source content for both versions
        from_source = db.query(JavaSourceFileVersion).join(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == from_version
        ).first()
        
        to_source = db.query(JavaSourceFileVersion).join(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == to_version
        ).first()
        
        if not from_source or not to_source:
            return "Source not found"
        
        from_content = from_source.file_content or ""
        to_content = to_source.file_content or ""
        
        if from_content == to_content:
            return "No differences found between versions"
        
        # Generate unified diff
        from_lines = from_content.splitlines(keepends=True)
        to_lines = to_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            from_lines,
            to_lines,
            fromfile=f"v{from_version}",
            tofile=f"v{to_version}",
            lineterm=""
        )
        
        diff_content = list(diff)[2:]  # Skip file headers
        
        if not diff_content:
            return "No differences found between versions"
        
        # Remove empty lines between diff lines and fix line endings
        filtered_content = []
        for line in diff_content:
            if line.strip() or line.startswith(('@@', '---', '+++')):
                # Remove trailing newlines to prevent double spacing
                filtered_content.append(line.rstrip('\n'))
        
        # Format as markdown with HTML anchor
        class_anchor_id = str(uuid.uuid4()).replace('-', '')[:16]
        result = f'<a id="{class_anchor_id}"/>\n'
        result += f"#### {class_name}\n\n"
        result += "```diff\n"
        result += "\n".join(filtered_content)
        result += "\n```"
        
        return result
    except Exception as e:
        return f"Error generating diff: {str(e)}"

def analyze_critical_differences(from_content, to_content, context_info=None):
    """
    Analyze critical differences that may cause compatibility issues:
    - Removed classes
    - Removed methods
    - Modified method signatures
    """
    if not from_content or not to_content:
        return []
    
    critical_changes = []
    
    # Parse Java source code to extract class and method definitions
    def extract_definitions(content):
        definitions = {
            'classes': set(),
            'methods': set()
        }
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Extract class definitions (public class, private class, etc.)
            class_match = re.match(r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?class\s+(\w+)', line)
            if class_match:
                definitions['classes'].add(class_match.group(1))
            
            # Extract method definitions (public, private, protected methods)
            method_match = re.match(r'^\s*(?:public|private|protected)\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:native\s+)?(?:strictfp\s+)?(?:<.*?>\s+)?(?:void|\w+(?:<.*?>)?)\s+(\w+)\s*\(', line)
            if method_match:
                # Store method signature (name + parameters)
                method_name = method_match.group(1)
                # Extract full method signature for comparison
                method_sig_match = re.search(r'(\w+)\s*\([^)]*\)', line)
                if method_sig_match:
                    definitions['methods'].add(method_sig_match.group(0))
        
        return definitions
    
    from_defs = extract_definitions(from_content)
    to_defs = extract_definitions(to_content)
    
    # Check for removed classes
    removed_classes = from_defs['classes'] - to_defs['classes']
    for class_name in removed_classes:
        change = {
            'type': 'removed_class',
            'description': f"Class '{class_name}' was removed",
            'severity': 'high'
        }
        if context_info:
            change['location'] = context_info
        critical_changes.append(change)
    
    # Check for removed methods
    removed_methods = from_defs['methods'] - to_defs['methods']
    for method_sig in removed_methods:
        change = {
            'type': 'removed_method',
            'description': f"Method '{method_sig}' was removed",
            'severity': 'high'
        }
        if context_info:
            change['location'] = context_info
        critical_changes.append(change)
    
    # Check for modified method signatures using diff
    from_lines = from_content.splitlines()
    to_lines = to_content.splitlines()
    
    diff = difflib.unified_diff(from_lines, to_lines, lineterm="")
    diff_lines = list(diff)[2:]  # Skip file headers
    
    for line in diff_lines:
        if line.startswith('-') and not line.startswith('---'):
            # Check if this is a method definition line
            method_match = re.match(r'^-\s*(?:public|private|protected)\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:native\s+)?(?:strictfp\s+)?(?:<.*?>\s+)?(?:void|\w+(?:<.*?>)?)\s+(\w+)\s*\(', line[1:].strip())
            if method_match:
                method_name = method_match.group(1)
                # Check if there's a corresponding + line (modified method)
                for next_line in diff_lines[diff_lines.index(line)+1:]:
                    if next_line.startswith('+') and not next_line.startswith('+++'):
                        next_method_match = re.match(r'^\+\s*(?:public|private|protected)\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?(?:native\s+)?(?:strictfp\s+)?(?:<.*?>\s+)?(?:void|\w+(?:<.*?>)?)\s+(\w+)\s*\(', next_line[1:].strip())
                        if next_method_match and next_method_match.group(1) == method_name:
                            change = {
                                'type': 'modified_method_signature',
                                'description': f"Method '{method_name}' signature was modified",
                                'severity': 'high',
                                'details': f"From: {line[1:].strip()}\nTo: {next_line[1:].strip()}"
                            }
                            if context_info:
                                change['location'] = context_info
                            critical_changes.append(change)
                            break
    
    return critical_changes

def format_critical_changes(critical_changes):
    """Format critical changes for display"""
    if not critical_changes:
        return "No critical compatibility issues found."
    
    result = []
    result.append("## ⚠️ Critical Compatibility Issues")
    result.append("")
    
    for change in critical_changes:
        severity_icon = "🔴" if change['severity'] == 'high' else "🟡"
        result.append(f"### {severity_icon} {change['type'].replace('_', ' ').title()}")
        result.append("")
        result.append(f"**Issue:** {change['description']}")
        result.append("")
        
        if 'details' in change:
            result.append("**Details:**")
            result.append("```diff")
            result.append(change['details'])
            result.append("```")
            result.append("")
    
    return "\n".join(result)

def format_file_size(bytes):
    if not bytes:
        return "0 B"
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB']
    i = int(math.floor(math.log(bytes) / math.log(k)))
    return f"{round(bytes / math.pow(k, i), 2)} {sizes[i]}"

@app.get("/api/java-sources/{class_full_name}/details", response_model=Dict[str, Any])
async def get_java_source_details(
    class_full_name: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a Java source file"""
    # Get the Java source file
    java_source = db.query(JavaSourceFile).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).first()
    
    if not java_source:
        raise HTTPException(status_code=404, detail="Java source file not found")
    
    # Get JAR files containing this source
    jar_files = db.query(JarFile, JavaSourceFileVersion.version).join(
        JavaSourceInJarFile, JarFile.id == JavaSourceInJarFile.jar_file_id
    ).join(
        JavaSourceFileVersion, JavaSourceInJarFile.java_source_file_version_id == JavaSourceFileVersion.id
    ).join(
        JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
    ).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).all()
    
    # Get Class files containing this source
    class_files = db.query(ClassFile, JavaSourceFileVersion.version).join(
        JavaSourceFileVersion, ClassFile.java_source_file_version_id == JavaSourceFileVersion.id
    ).join(
        JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
    ).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).all()
    
    result = {
        "class_full_name": class_full_name,
        "jar_files": [],
        "class_files": []
    }
    
    # Process JAR files
    for jar_file, version in jar_files:
        result["jar_files"].append({
            "jar_name": jar_file.jar_name,
            "version_no": jar_file.version_no,
            "last_version_no": jar_file.last_version_no,
            "last_modified": jar_file.last_modified.isoformat() if jar_file.last_modified else None,
            "file_size": jar_file.file_size,
            "service_id": jar_file.service_id,
            "source_version": version
        })
    
    # Process Class files
    for class_file, version in class_files:
        result["class_files"].append({
            "class_full_name": class_file.class_full_name,
            "version_no": class_file.version_no,
            "last_version_no": class_file.last_version_no,
            "last_modified": class_file.last_modified.isoformat() if class_file.last_modified else None,
            "file_size": class_file.file_size,
            "service_id": class_file.service_id,
            "source_version": version
        })
    
    return result

@app.get("/api/jars/{jar_name}/versions", response_model=VersionHistory)
async def get_jar_versions(jar_name: str):
    db = SessionLocal()
    try:
        # 获取JAR文件版本信息
        versions_query = db.query(
            JarFile.version_no,
            func.min(JarFile.file_size).label('file_size'),
            func.min(JarFile.last_modified).label('earliest_time'),
            func.max(JarFile.last_modified).label('latest_time'),
            func.count(func.distinct(JarFile.service_id)).label('service_count'),
            func.min(JarFile.source_hash).label('source_hash')  # 添加source_hash
        ).filter(
            JarFile.jar_name == jar_name,
            JarFile.is_third_party == False
        ).group_by(JarFile.version_no).order_by(JarFile.version_no)
        
        versions = []
        for row in versions_query.all():
            # 获取使用该版本的服务列表
            services = db.query(Service.id, Service.service_name).join(JarFile).filter(
                JarFile.jar_name == jar_name,
                JarFile.version_no == row.version_no,
                JarFile.is_third_party == False
            ).distinct().all()
            
            # 计算该JAR版本包含的源码文件数量
            source_file_count = db.query(func.count(func.distinct(JavaSourceInJarFile.java_source_file_version_id))).join(
                JarFile, JavaSourceInJarFile.jar_file_id == JarFile.id
            ).filter(
                JarFile.jar_name == jar_name,
                JarFile.version_no == row.version_no,
                JarFile.is_third_party == False
            ).scalar() or 0
            
            versions.append(VersionInfo(
                version_no=row.version_no,
                file_size=row.file_size,
                earliest_time=row.earliest_time.isoformat(),
                latest_time=row.latest_time.isoformat(),
                service_count=row.service_count,
                services=[ServiceInfo(id=s.id, name=s.service_name) for s in services],
                file_count=source_file_count,
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
            services = db.query(Service.id, Service.service_name).join(ClassFile).filter(
                ClassFile.class_full_name == class_name,
                ClassFile.version_no == row.version_no
            ).distinct().all()
            
            versions.append(VersionInfo(
                version_no=row.version_no,
                file_size=row.file_size,
                earliest_time=row.earliest_time.isoformat(),
                latest_time=row.latest_time.isoformat(),
                service_count=row.service_count,
                services=[ServiceInfo(id=s.id, name=s.service_name) for s in services],
                file_count=row.file_count
            ))
        
        return VersionHistory(
            item_name=class_name,
            item_type="class",
            versions=versions
        )
        
    finally:
        db.close()

@app.get("/api/classes/{class_name}/diff")
async def get_class_diff(
    class_name: str,
    from_version: int = Query(..., description="源版本号"),
    to_version: int = Query(..., description="目标版本号"),
    file_path: Optional[str] = Query(None, description="特定文件路径"),
    resp_format: str = Query("structured", alias="format", description="返回格式: structured 或 unified"),
    include: str = Query("all", description="unified模式返回内容: diff|content|all")
):
    """获取Class文件版本差异"""
    db = SessionLocal()
    try:
        # 获取两个版本的Class文件
        from_class = db.query(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == from_version
        ).first()
        
        to_class = db.query(ClassFile).filter(
            ClassFile.class_full_name == class_name,
            ClassFile.version_no == to_version
        ).first()
        
        if not from_class or not to_class:
            raise HTTPException(status_code=404, detail="Class file version not found")
        
        # 获取对应的Java源码文件版本
        from_source = db.query(JavaSourceFileVersion).filter(
            JavaSourceFileVersion.id == from_class.java_source_file_version_id
        ).first()
        
        to_source = db.query(JavaSourceFileVersion).filter(
            JavaSourceFileVersion.id == to_class.java_source_file_version_id
        ).first()
        
        if not from_source or not to_source:
            raise HTTPException(status_code=404, detail="Source file version not found")
        
        # 计算差异
        from_content = from_source.file_content or ""
        to_content = to_source.file_content or ""
        
        # 计算行数差异
        from_lines = from_content.split('\n')
        to_lines = to_content.split('\n')
        
        diff = list(difflib.unified_diff(from_lines, to_lines, lineterm=''))
        additions = len([line for line in diff if line.startswith('+') and not line.startswith('+++')])
        deletions = len([line for line in diff if line.startswith('-') and not line.startswith('---')])
        
        changes = additions + deletions
        change_percentage = (changes / max(len(from_lines), 1)) * 100
        
        # 生成差异内容
        file_changes = [FileChange(
            file_path=f"{class_name}.java",
            change_type="modified" if from_content != to_content else "unchanged",
            additions=additions,
            deletions=deletions,
            changes=changes,
            change_percentage=round(change_percentage, 1),
            size_before=from_source.file_size or 0,
            size_after=to_source.file_size or 0,
            class_full_name=class_name
        )]
        
        summary = DiffSummary(
            total_files=1,
            files_changed=1 if from_content != to_content else 0,
            insertions=additions,
            deletions=deletions,
            net_change=additions - deletions
        )
        
        # 如果请求特定文件
        if file_path:
            if resp_format == "unified":
                # 生成unified diff文本
                unified_list = list(
                    difflib.unified_diff(
                        from_lines,
                        to_lines,
                        fromfile=f"a/{class_name}.java",
                        tofile=f"b/{class_name}.java",
                        lineterm=""
                    )
                )
                
                unified_text = []
                unified_text.append(f"diff --git a/{class_name}.java b/{class_name}.java")
                unified_text.append(f"--- a/{class_name}.java")
                unified_text.append(f"+++ b/{class_name}.java")
                # 过滤掉unified_list中重复的---和+++行
                filtered_unified = [line for line in unified_list if not line.startswith('---') and not line.startswith('+++')]
                unified_text.extend(filtered_unified)
                unified_str = "\n".join(unified_text)
                
                return {
                    "file_path": f"{class_name}.java",
                    "unified_diff": unified_str
                }
            else:
                return {
                    "from_content": from_content,
                    "to_content": to_content
                }
        
        if resp_format == "unified":
            # 生成unified diff文本
            unified_list = list(
                difflib.unified_diff(
                    from_lines,
                    to_lines,
                    fromfile=f"a/{class_name}.java",
                    tofile=f"b/{class_name}.java",
                    lineterm=""
                )
            )
            
            unified_text = []
            unified_text.append(f"diff --git a/{class_name}.java b/{class_name}.java")
            unified_text.append(f"--- a/{class_name}.java")
            unified_text.append(f"+++ b/{class_name}.java")
            # 过滤掉unified_list中重复的---和+++行
            filtered_unified = [line for line in unified_list if not line.startswith('---') and not line.startswith('+++')]
            unified_text.extend(filtered_unified)
            unified_str = "\n".join(unified_text)
            
            return {
                "from_version": from_version,
                "to_version": to_version,
                "summary": summary.model_dump() if hasattr(summary, "model_dump") else summary.__dict__,
                "files": [{
                    "file_path": f"{class_name}.java",
                    "change_type": "modified" if from_content != to_content else "unchanged",
                    "additions": additions,
                    "deletions": deletions,
                    "unified_diff": unified_str,
                    "language": "java",
                    "class_full_name": class_name
                }]
            }
        else:
            # 生成结构化差异
            file_diffs = []
            if from_content != to_content:
                hunks = generate_diff_hunks(from_content, to_content)
                file_diffs.append(FileDiff(
                    file_path=f"{class_name}.java",
                    hunks=hunks
                ))
            
            return VersionDiff(
                from_version=from_version,
                to_version=to_version,
                file_changes=file_changes,
                summary=summary,
                file_diffs=file_diffs
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
            
            # 只有当文件真正有变更时才添加到file_changes列表
            if changes > 0:
                change_percentage = (changes / max(len(from_file.file_content.split('\n')) if from_file else 1, 1)) * 100
                
                file_changes.append(FileChange(
                    file_path=display_path,
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                    changes=changes,
                    change_percentage=round(change_percentage, 1),
                    size_before=from_file.file_size if from_file else 0,
                    size_after=to_file.file_size if to_file else 0,
                    class_full_name=class_name
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
                            "language": "java",
                            "class_full_name": class_name
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
                            "language": "java",
                            "class_full_name": class_name
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
                    "language": "java",
                    "class_full_name": class_name
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
                    "language": "java",
                    "class_full_name": class_name
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
            files_changed=len(file_changes),
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

@app.get("/api/java-sources/{class_full_name}/versions")
async def get_java_source_versions(
    class_full_name: str,
    db: Session = Depends(get_db)
):
    """Get version history for a Java source file"""
    # Get all versions of this Java source file that are actually used by JAR or Class files
    # First, get all source versions that are referenced by JAR files
    jar_source_versions = db.query(JavaSourceFileVersion).join(
        JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
    ).join(
        JavaSourceInJarFile, JavaSourceFileVersion.id == JavaSourceInJarFile.java_source_file_version_id
    ).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).distinct().all()
    
    # Get all source versions that are referenced by Class files
    class_source_versions = db.query(JavaSourceFileVersion).join(
        JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
    ).join(
        ClassFile, JavaSourceFileVersion.id == ClassFile.java_source_file_version_id
    ).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).distinct().all()
    
    # Combine and deduplicate the versions
    all_versions = {}
    for version in jar_source_versions + class_source_versions:
        all_versions[version.id] = version
    
    if not all_versions:
        raise HTTPException(status_code=404, detail="Java source file not found")
    
    result = []
    for version in sorted(all_versions.values(), key=lambda x: x.id, reverse=True):
        # Get JAR files containing this version
        jar_files = db.query(JarFile, Service.service_name).join(
            JavaSourceInJarFile, JarFile.id == JavaSourceInJarFile.jar_file_id
        ).join(
            Service, JarFile.service_id == Service.id
        ).filter(
            JavaSourceInJarFile.java_source_file_version_id == version.id
        ).all()
        
        # Get Class files containing this version
        class_files = db.query(ClassFile, Service.service_name).join(
            Service, ClassFile.service_id == Service.id
        ).filter(
            ClassFile.java_source_file_version_id == version.id
        ).all()
        
        # Collect services and determine the actual version numbers
        services = set()
        jar_services = []
        class_services = []
        
        # Use version_no from JAR/Class files as the actual version
        actual_version = None
        
        for jar_file, service_name in jar_files:
            services.add(service_name)
            if actual_version is None:
                actual_version = jar_file.version_no
            jar_services.append({
                "jar_name": jar_file.jar_name,
                "version_no": jar_file.version_no,
                "last_version_no": jar_file.last_version_no,
                "service_name": service_name,
                "service_id": jar_file.service_id,
                "last_modified": jar_file.last_modified.isoformat() if jar_file.last_modified else None,
                "file_size": jar_file.file_size
            })
        
        for class_file, service_name in class_files:
            services.add(service_name)
            if actual_version is None:
                actual_version = class_file.version_no
            class_services.append({
                "class_full_name": class_file.class_full_name,
                "version_no": class_file.version_no,
                "last_version_no": class_file.last_version_no,
                "service_name": service_name,
                "service_id": class_file.service_id,
                "last_modified": class_file.last_modified.isoformat() if class_file.last_modified else None,
                "file_size": class_file.file_size
            })
        
        # Only include versions that have associated JAR or Class files
        if jar_services or class_services:
            # Use the source file version ID as a fallback if no JAR/Class files
            if actual_version is None:
                actual_version = version.id
            
            result.append({
                "version": actual_version,
                "source_version_id": version.id,  # Keep the source version ID for reference
                "file_size": version.file_size,
                "file_hash": version.file_hash,
                "created_at": version.created_at.isoformat() if version.created_at else None,
                "service_count": len(services),
                "services": list(services),
                "jar_files": jar_services,
                "class_files": class_services
            })
    
    return result

@app.get("/api/java-sources/{class_full_name}/diff/{from_version}/{to_version}")
async def get_java_source_diff(
    class_full_name: str,
    from_version: int,
    to_version: int,
    db: Session = Depends(get_db)
):
    """Get diff between two versions of a Java source file"""
    # First get the source versions to find the source_version_id
    source_versions = db.query(JavaSourceFileVersion).join(
        JavaSourceFile, JavaSourceFileVersion.java_source_file_id == JavaSourceFile.id
    ).filter(
        JavaSourceFile.class_full_name == class_full_name
    ).order_by(JavaSourceFileVersion.id.desc()).all()
    
    if not source_versions:
        raise HTTPException(status_code=404, detail="Java source file not found")
    
    # Find the source versions that correspond to the requested version numbers
    from_source_version = None
    to_source_version = None
    
    for version in source_versions:
        # Check if this version corresponds to the requested version number
        # by looking at associated JAR/Class files
        jar_files = db.query(JarFile).join(
            JavaSourceInJarFile, JarFile.id == JavaSourceInJarFile.jar_file_id
        ).filter(
            JavaSourceInJarFile.java_source_file_version_id == version.id
        ).all()
        
        class_files = db.query(ClassFile).filter(
            ClassFile.java_source_file_version_id == version.id
        ).all()
        
        # Determine the actual version number for this source version
        actual_version = None
        if jar_files:
            actual_version = jar_files[0].version_no
        elif class_files:
            actual_version = class_files[0].version_no
        else:
            actual_version = version.id  # fallback
        
        if actual_version == from_version:
            from_source_version = version
        if actual_version == to_version:
            to_source_version = version
    
    if not from_source_version or not to_source_version:
        raise HTTPException(status_code=404, detail="Source version not found")
    
    # Get source content
    from_content = from_source_version.file_content or ""
    to_content = to_source_version.file_content or ""
    
    # Generate diff
    from difflib import unified_diff
    diff_lines = list(unified_diff(
        from_content.splitlines(keepends=True),
        to_content.splitlines(keepends=True),
        fromfile=f"{class_full_name} (v{from_version})",
        tofile=f"{class_full_name} (v{to_version})",
        lineterm=""
    ))
    
    # Calculate statistics
    additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
    
    return {
        "class_full_name": class_full_name,
        "from_version": from_version,
        "to_version": to_version,
        "unified_diff": ''.join(diff_lines),
        "additions": additions,
        "deletions": deletions,
        "files_changed": 1 if additions > 0 or deletions > 0 else 0,
        "from_content": from_content,
        "to_content": to_content,
        "has_changes": additions > 0 or deletions > 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
