from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import (
    get_current_user, 
    get_authenticated_user,
    require_permission,
    require_role,
    rate_limit,
    audit_log
)
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserProfile,
    UserPermissions,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    UserUpdate,
    UserList,
    AuditLogResponse,
    PasswordReset,
    PasswordResetConfirm,
    PasswordChange
)
from app.models.auth import APIKey, AuditLog
from app.models.users import User
from app.services.auth_service import auth_service
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=UserProfile)
@audit_log("user_management", "user")
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit)
):
    """
    Register a new user account
    
    - **email**: Valid email address
    - **password**: Strong password (8+ chars, upper, lower, digit)
    - **full_name**: User's full name
    - **department**: Optional department assignment
    """
    
    try:
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            department=user_data.department
        )
        
        return UserProfile.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
@audit_log("authentication", "user")
async def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit)
):
    """
    Authenticate user and return access token
    
    - **email**: User's email address
    - **password**: User's password
    """
    
    # Authenticate user
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        # Log failed login attempt
        auth_service.log_audit_event(
            db=db,
            user_id=None,
            event_type="authentication",
            action="login_failed",
            status="failure",
            ip_address=request.client.host if request.client else None,
            error_message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = auth_service.create_access_token(token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfile.from_orm(user)
    )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile information"""
    return UserProfile.from_orm(current_user)

@router.put("/me", response_model=UserProfile)
@audit_log("user_management", "user")
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile (limited fields)"""
    
    # Users can only update certain fields themselves
    allowed_updates = ["full_name", "department"]
    
    for field, value in user_update.dict(exclude_unset=True).items():
        if field in allowed_updates and value is not None:
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserProfile.from_orm(current_user)

@router.post("/change-password")
@audit_log("authentication", "user")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    
    # Verify current password
    if not auth_service.verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = auth_service.hash_password(password_change.new_password)
    current_user.password_changed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.post("/api-keys", response_model=APIKeyCreateResponse)
@audit_log("api_management", "api_key")
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for the current user"""
    
    # Check if user already has too many API keys
    existing_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()
    
    if existing_keys >= 5:  # Limit to 5 active API keys per user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys reached (5)"
        )
    
    key_info = auth_service.generate_api_key(db, current_user.id, key_data.name)
    
    return APIKeyCreateResponse(**key_info)

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List current user's API keys"""
    
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return [APIKeyResponse.from_orm(key) for key in api_keys]

@router.delete("/api-keys/{key_id}")
@audit_log("api_management", "api_key")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}

# Admin endpoints
@router.get("/users", response_model=UserList)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    department: Optional[str] = None,
    role: Optional[str] = None,
    admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    
    query = db.query(User)
    
    # Apply filters
    if department:
        query = query.filter(User.department == department)
    if role:
        query = query.filter(User.role == role)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return UserList(
        users=[UserProfile.from_orm(user) for user in users],
        total_count=total_count,
        page=page,
        page_size=page_size
    )

@router.put("/users/{user_id}", response_model=UserProfile)
@audit_log("user_management", "user")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    for field, value in user_update.dict(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserProfile.from_orm(user)

@router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = 1,
    page_size: int = 50,
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get audit logs (admin only)"""
    
    query = db.query(AuditLog)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    # Order by timestamp descending
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    logs = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return AuditLogResponse(
        logs=[AuditLogEntry.from_orm(log) for log in logs],
        total_count=total_count,
        page=page,
        page_size=page_size
    )

@router.get("/permissions", response_model=UserPermissions)
async def get_user_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user's permissions summary"""
    return auth_service.get_user_permissions_summary(current_user)