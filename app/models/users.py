# app/models/users.py - FINAL UNIFIED VERSION
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    """Unified User model with both basic and authentication fields"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic user information (for chat system)
    name = Column(String(255), nullable=False)  # Keep this for chat compatibility
    email = Column(String(255), unique=True, nullable=False, index=True)
    department = Column(String(100), index=True)
    role = Column(String(50), default="employee")  # "employee", "manager", "admin"
    
    # Authentication fields (for auth system)
    full_name = Column(String(255), nullable=True)  # Optional, can be same as 'name'
    hashed_password = Column(String(255), nullable=True)  # Nullable for users created via chat
    is_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    
    # Permissions
    can_upload_documents = Column(Boolean, default=True)
    can_delete_documents = Column(Boolean, default=False)
    can_access_analytics = Column(Boolean, default=False)
    
    # Status and timestamps
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    last_active = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")