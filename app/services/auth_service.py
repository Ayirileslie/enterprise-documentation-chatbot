import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.auth import APIKey, AuditLog, PasswordResetToken
from app.models.users import User
from app.core.config import get_settings

settings = get_settings()

class AuthService:
    def __init__(self):
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT settings
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storing"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
            
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    def create_user(
        self, 
        db: Session,
        email: str,
        password: str,
        full_name: str,
        department: str = None,
        role: str = "employee"
    ) -> User:
        """Create a new user"""
        
        # Check if user already exists
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            department=department,
            role=role,
            is_active=True,
            is_verified=True  # Auto-verify for now, implement email verification later
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def generate_api_key(self, db: Session, user_id: int, key_name: str) -> Dict[str, str]:
        """Generate a new API key for a user"""
        
        # Generate random key
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_prefix = key[:8]
        
        # Store in database
        api_key = APIKey(
            user_id=user_id,
            key_name=key_name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiry
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        return {
            "api_key": f"sk-{key}",
            "key_id": api_key.id,
            "expires_at": api_key.expires_at.isoformat()
        }
    
    def validate_api_key(self, db: Session, api_key: str) -> Optional[User]:
        """Validate an API key and return the associated user"""
        
        if not api_key.startswith("sk-"):
            return None
        
        key = api_key[3:]  # Remove 'sk-' prefix
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Find API key in database
        api_key_record = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key_record:
            return None
        
        # Check if expired
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            return None
        
        # Update usage
        api_key_record.last_used = datetime.utcnow()
        api_key_record.usage_count += 1
        db.commit()
        
        # Return associated user
        return db.query(User).filter(User.id == api_key_record.user_id).first()
    
    def log_audit_event(
        self,
        db: Session,
        user_id: Optional[int],
        event_type: str,
        action: str,
        status: str,
        resource_type: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        endpoint: str = None,
        http_method: str = None,
        error_message: str = None,
        additional_data: Dict = None
    ):
        """Log an audit event"""
        
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            http_method=http_method,
            status=status,
            error_message=error_message,
            additional_data=str(additional_data) if additional_data else None
        )
        
        db.add(audit_log)
        db.commit()
    
    def check_user_permissions(self, user: User, required_permission: str) -> bool:
        """Check if user has required permission"""
        
        permission_map = {
            "upload_documents": user.can_upload_documents,
            "delete_documents": user.can_delete_documents,
            "access_analytics": user.can_access_analytics,
            "admin": user.role == "admin",
            "manager": user.role in ["manager", "admin"]
        }
        
        return permission_map.get(required_permission, False)
    
    def create_password_reset_token(self, db: Session, email: str) -> Optional[str]:
        """Create a password reset token"""
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        # Generate token
        token = secrets.token_urlsafe(32)
        
        # Store in database
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        )
        
        db.add(reset_token)
        db.commit()
        
        return token
    
    def reset_password(self, db: Session, token: str, new_password: str) -> bool:
        """Reset password using token"""
        
        # Find token
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()
        
        if not reset_token:
            return False
        
        # Get user
        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return False
        
        # Update password
        user.hashed_password = self.hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.used_at = datetime.utcnow()
        
        db.commit()
        
        return True
    
    def get_user_permissions_summary(self, user: User) -> Dict[str, Any]:
        """Get a summary of user's permissions"""
        
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "department": user.department,
            "permissions": {
                "upload_documents": user.can_upload_documents,
                "delete_documents": user.can_delete_documents,
                "access_analytics": user.can_access_analytics,
                "is_admin": user.role == "admin",
                "is_manager": user.role in ["manager", "admin"]
            },
            "account_status": {
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat()
            }
        }

# Global instance
auth_service = AuthService()