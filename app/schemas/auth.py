from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

# Authentication request schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

# Authentication response schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserProfile"

class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    department: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    # Permissions
    can_upload_documents: bool
    can_delete_documents: bool
    can_access_analytics: bool
    
    model_config = ConfigDict(from_attributes=True)

class UserPermissions(BaseModel):
    user_id: int
    email: str
    role: str
    department: Optional[str]
    permissions: Dict[str, bool]
    account_status: Dict[str, Any]

class APIKeyResponse(BaseModel):
    id: int
    key_name: str
    key_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int
    is_active: bool

class APIKeyCreateResponse(BaseModel):
    api_key: str
    key_id: int
    expires_at: str
    warning: str = "Store this API key securely. It will not be shown again."

# Admin schemas
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(employee|manager|admin)$")
    is_active: Optional[bool] = None
    can_upload_documents: Optional[bool] = None
    can_delete_documents: Optional[bool] = None
    can_access_analytics: Optional[bool] = None

class UserList(BaseModel):
    users: List[UserProfile]
    total_count: int
    page: int
    page_size: int

# Audit schemas
class AuditLogEntry(BaseModel):
    id: int
    user_id: Optional[int]
    event_type: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    status: str
    ip_address: Optional[str]
    timestamp: datetime
    error_message: Optional[str]

class AuditLogResponse(BaseModel):
    logs: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int

# Rate limiting schemas
class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None

class RateLimitExceeded(BaseModel):
    error: str = "Rate limit exceeded"
    limit: int
    retry_after: int
    message: str

# Resolve forward references
Token.model_rebuild()