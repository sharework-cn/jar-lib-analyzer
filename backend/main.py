# Source Code Difference Analysis System - Backend
# FastAPI-based web service

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime
import hashlib

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://jal:271828@172.30.80.95:32306/jal")

# Create database engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create FastAPI app
app = FastAPI(title="Source Code Difference Analysis API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
