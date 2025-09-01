import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import logging
import time

from app.api import documents, chat, auth
from app.core.database import create_tables, get_db
from app.core.config import get_settings, validate_configuration
from app.core.security import security_middleware, rate_limit
from app.services.auth_service import auth_service
from app.models.users import User
from app.core.security import require_role

# Load environment variables
load_dotenv()

# Validate configuration
if not validate_configuration():
    raise SystemExit("Configuration validation failed")

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered chatbot for company documentation with enterprise security",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Security middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure for your domain in production
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Add rate limit headers if they exist
    if hasattr(request.state, 'rate_limit_headers'):
        for header, value in request.state.rate_limit_headers.items():
            response.headers[header] = value
    
    # Log response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
    
    return response

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url)
        }
    )

# Include API routers
app.include_router(auth.router, dependencies=[Depends(rate_limit)])
app.include_router(documents.router, dependencies=[Depends(rate_limit)])
app.include_router(chat.router, dependencies=[Depends(rate_limit)])

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created/verified")
    
    # Create admin user if specified
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        try:
            db = next(get_db())
            existing_admin = db.query(User).filter(
                User.email == settings.ADMIN_EMAIL
            ).first()
            
            if not existing_admin:
                admin_user = auth_service.create_user(
                    db=db,
                    email=settings.ADMIN_EMAIL,
                    password=settings.ADMIN_PASSWORD,
                    full_name="System Administrator",
                    role="admin"
                )
                admin_user.can_upload_documents = True
                admin_user.can_delete_documents = True
                admin_user.can_access_analytics = True
                db.commit()
                logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")
            else:
                logger.info("Admin user already exists")
                
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
    
    logger.info("API is ready!")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}")

# Root endpoints
@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "features": [
            "User authentication & authorization",
            "Document upload and processing",
            "Semantic document search",
            "AI-powered chat responses",
            "Conversation management",
            "RAG (Retrieval-Augmented Generation)",
            "Role-based access control",
            "API key management",
            "Audit logging",
            "Rate limiting"
        ],
        "endpoints": {
            "auth": "/api/auth/login",
            "register": "/api/auth/register",
            "docs": "/docs" if settings.DEBUG else "disabled",
            "chat": "/api/chat/message",
            "documents": "/api/documents/upload"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "vector_store": "connected",
        "llm": "configured" if settings.OPENAI_API_KEY else "not_configured",
        "auth": "enabled",
        "rate_limiting": "enabled" if settings.RATE_LIMIT_ENABLED else "disabled"
    }

# System info endpoint (admin only)
@app.get("/system/info")
async def system_info(
    admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get system information (admin only)"""
    
    # Get database stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    from app.models.conversations import Conversation, Message
    from app.models.documents import Document
    
    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()
    total_documents = db.query(Document).count()
    
    return {
        "system": {
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug_mode": settings.DEBUG,
            "rate_limiting": settings.RATE_LIMIT_ENABLED
        },
        "database": {
            "total_users": total_users,
            "active_users": active_users,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_documents": total_documents
        },
        "configuration": {
            "max_file_size": f"{settings.MAX_FILE_SIZE / (1024*1024):.1f}MB",
            "allowed_extensions": settings.ALLOWED_FILE_EXTENSIONS,
            "rate_limit_per_hour": settings.RATE_LIMIT_REQUESTS_PER_HOUR,
            "token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        }
    }