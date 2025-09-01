import time
from typing import Optional, Dict, Callable
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import redis
from collections import defaultdict
import asyncio

from app.core.database import get_db
from app.core.config import get_settings
from app.models.auth import RateLimitLog
from app.models.users import User
from app.services.auth_service import auth_service

settings = get_settings()

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)

class SecurityMiddleware:
    def __init__(self):
        # In-memory rate limiting (use Redis in production)
        self.rate_limits = defaultdict(list)
        self.blocked_ips = {}
        
        # Initialize Redis if available
        self.redis_client = None
        try:
            if settings.is_production:
                import redis
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        except ImportError:
            pass
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, identifier: str, endpoint: str, limit_per_hour: int = 1000) -> tuple[bool, int]:
        """Check if identifier is rate limited"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self.rate_limits[f"{identifier}:{endpoint}"] = [
            timestamp for timestamp in self.rate_limits[f"{identifier}:{endpoint}"]
            if timestamp > hour_ago
        ]
        
        current_count = len(self.rate_limits[f"{identifier}:{endpoint}"])
        
        if current_count >= limit_per_hour:
            return True, 0  # Rate limited, no remaining requests
        
        # Add current request
        self.rate_limits[f"{identifier}:{endpoint}"].append(now)
        
        return False, limit_per_hour - current_count - 1
    
    def block_ip(self, ip_address: str, duration_minutes: int = 60):
        """Block an IP address temporarily"""
        self.blocked_ips[ip_address] = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        if ip_address in self.blocked_ips:
            if datetime.utcnow() > self.blocked_ips[ip_address]:
                del self.blocked_ips[ip_address]
                return False
            return True
        return False
    
    async def log_rate_limit(self, db: Session, identifier: str, endpoint: str, blocked: bool = False):
        """Log rate limiting events"""
        try:
            rate_log = RateLimitLog(
                identifier=identifier,
                identifier_type="ip",
                endpoint=endpoint,
                requests_count=1,
                window_start=datetime.utcnow(),
                is_blocked=blocked,
                block_until=datetime.utcnow() + timedelta(hours=1) if blocked else None
            )
            
            db.add(rate_log)
            db.commit()
        except Exception as e:
            print(f"Failed to log rate limit: {e}")

# Dependency functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode JWT token
        payload = auth_service.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

async def get_api_key_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get user from API key authentication"""
    
    # Check for API key in header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    user = auth_service.validate_api_key(db, api_key)
    if not user or not user.is_active:
        return None
    
    return user

async def get_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get authenticated user via JWT or API key"""
    
    # Try API key first
    user = await get_api_key_user(request, db)
    if user:
        return user
    
    # Fall back to JWT
    return await get_current_user(credentials, db)

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not auth_service.check_user_permissions(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return user
    return permission_checker

def require_role(role: str):
    """Decorator to require specific role"""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role and user.role != "admin":  # Admin can access everything
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return user
    return role_checker

# Rate limiting dependency
security_middleware = SecurityMiddleware()

async def rate_limit(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Apply rate limiting to requests"""
    
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    # Get identifier for rate limiting
    if user:
        identifier = f"user:{user.id}"
        limit_per_hour = 2000  # Higher limit for authenticated users
    else:
        identifier = f"ip:{security_middleware.get_client_ip(request)}"
        limit_per_hour = settings.RATE_LIMIT_REQUESTS_PER_HOUR
    
    endpoint = f"{request.method}:{request.url.path}"
    
    # Check if blocked
    ip_address = security_middleware.get_client_ip(request)
    if security_middleware.is_ip_blocked(ip_address):
        await security_middleware.log_rate_limit(db, identifier, endpoint, blocked=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP address temporarily blocked due to rate limit violations"
        )
    
    # Check rate limit
    is_limited, remaining = security_middleware.is_rate_limited(
        identifier, endpoint, limit_per_hour
    )
    
    if is_limited:
        # Block IP after repeated violations
        security_middleware.block_ip(ip_address, duration_minutes=60)
        await security_middleware.log_rate_limit(db, identifier, endpoint, blocked=True)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_per_hour),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "3600"
            }
        )
    
    # Add rate limit headers
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit_per_hour),
        "X-RateLimit-Remaining": str(remaining)
    }

# Audit logging decorator
def audit_log(event_type: str, resource_type: str = None):
    """Decorator to automatically log audit events"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Extract request, user, and db from kwargs
            request = kwargs.get('request')
            user = kwargs.get('user') or kwargs.get('current_user')
            db = kwargs.get('db')
            
            user_id = user.id if user else None
            ip_address = security_middleware.get_client_ip(request) if request else None
            user_agent = request.headers.get("User-Agent") if request else None
            endpoint = f"{request.method}:{request.url.path}" if request else None
            
            try:
                # Execute the original function
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # Log success
                if db:
                    auth_service.log_audit_event(
                        db=db,
                        user_id=user_id,
                        event_type=event_type,
                        action=func.__name__,
                        status="success",
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        endpoint=endpoint
                    )
                
                return result
                
            except Exception as e:
                # Log failure
                if db:
                    auth_service.log_audit_event(
                        db=db,
                        user_id=user_id,
                        event_type=event_type,
                        action=func.__name__,
                        status="failure",
                        resource_type=resource_type,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        endpoint=endpoint,
                        error_message=str(e)
                    )
                
                raise e
                
        return wrapper
    return decorator