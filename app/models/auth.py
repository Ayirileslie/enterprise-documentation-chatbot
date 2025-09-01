# app/models/auth.py - REMOVE the User class definition
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# NOTE: User class is now ONLY in app/models/users.py
# These models reference the User table but don't define the User class

class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # API key details
    key_name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification
    
    # Permissions and limits
    scopes = Column(Text)  # JSON array of allowed endpoints/actions
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # Relationship - references User table from users.py
    user = relationship("User", back_populates="api_keys")

class AuditLog(Base):
    """Security and activity audit logging"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for system events
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # login, upload, delete, etc.
    resource_type = Column(String(50))  # document, conversation, user, etc.
    resource_id = Column(String(50))  # ID of the affected resource
    action = Column(String(100), nullable=False)
    
    # Request context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    endpoint = Column(String(200))
    http_method = Column(String(10))
    
    # Result
    status = Column(String(20), nullable=False)  # success, failure, error
    error_message = Column(Text)
    
    # Metadata
    additional_data = Column(Text)  # JSON for extra context
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationship - references User table from users.py
    user = relationship("User", back_populates="audit_logs")

class PasswordResetToken(Base):
    """Password reset tokens"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    token = Column(String(255), nullable=False, unique=True, index=True)
    is_used = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True))

class RateLimitLog(Base):
    """Track API rate limiting"""
    __tablename__ = "rate_limit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifier (could be user ID, API key, or IP address)
    identifier = Column(String(255), nullable=False, index=True)
    identifier_type = Column(String(20), nullable=False)  # user, api_key, ip
    
    # Rate limit details
    endpoint = Column(String(200), nullable=False)
    requests_count = Column(Integer, default=1)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Status
    is_blocked = Column(Boolean, default=False)
    block_until = Column(DateTime(timezone=True))