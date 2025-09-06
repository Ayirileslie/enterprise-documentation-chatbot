import os
from functools import lru_cache
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    GEMINI_API_KEY: Optional[str] = None
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    MAX_MESSAGE_LENGTH: int = 2000
    
    # Basic App Settings
    APP_NAME: str = "Company Documentation Chatbot API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # Security Settings
    SECRET_KEY: str = Field(..., min_length=32, description="JWT secret key (min 32 chars)")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440, description="Token expiry in minutes")
    
    # Database Settings
    DATABASE_URL: str = Field(default="sqlite:///./data/database.db", description="Database connection URL")
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    
    # ChromaDB Settings
    CHROMA_DB_PATH: str = Field(default="./data/chroma_db", description="ChromaDB storage path")
    
    # OpenAI Settings
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    OPENAI_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    OPENAI_MAX_TOKENS: int = Field(default=1000, ge=100, le=4096, description="Max tokens in response")
    
    # Embedding Settings
    GEMINI_EMBEDDING_MODEL: str = Field(default="models/embedding-001", description="Gemini embedding model")
    EMBEDDING_DIMENSION: int = Field(default=768, ge=100, le=1536, description="Embedding vector size")
    
    # RAG Settings
    MAX_CONVERSATION_MEMORY: int = Field(default=5, ge=1, le=20, description="Conversation history length")
    DEFAULT_RETRIEVAL_COUNT: int = Field(default=4, ge=1, le=10, description="Documents to retrieve")
    CHUNK_SIZE: int = Field(default=1000, ge=100, le=2000, description="Document chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=200, ge=0, le=500, description="Chunk overlap in characters")
    
    # File Upload Settings
    MAX_FILE_SIZE: int = Field(default=10*1024*1024, ge=1024, le=100*1024*1024, description="Max file size in bytes")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(default=[".pdf", ".docx", ".txt", ".md"], description="Allowed file types")
    UPLOAD_DIR: str = Field(default="./data/documents", description="File upload directory")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, ge=10, le=1000)
    RATE_LIMIT_REQUESTS_PER_HOUR: int = Field(default=1000, ge=100, le=10000)
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    
    # CORS Settings
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    CORS_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    CORS_METHODS: List[str] = Field(default=["*"], description="Allowed HTTP methods")
    CORS_HEADERS: List[str] = Field(default=["*"], description="Allowed HTTP headers")
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FILE: str = Field(default="./logs/app.log", description="Log file path")
    LOG_MAX_SIZE: str = Field(default="10MB", description="Max log file size")
    LOG_BACKUP_COUNT: int = Field(default=5, ge=1, le=30, description="Number of backup log files")
    
    # Monitoring Settings
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PORT: int = Field(default=8090, ge=1024, le=65535)
    
    # Email Settings (for password reset, notifications)
    SMTP_SERVER: str = Field(default="", description="SMTP server address")
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USERNAME: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    EMAIL_FROM: str = Field(default="", description="From email address")
    
    # Admin Settings
    ADMIN_EMAIL: str = Field(default="", description="Default admin email")
    ADMIN_PASSWORD: str = Field(default="", description="Default admin password")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"  # Forbid extra fields
    )

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL for SQLAlchemy"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
        
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator('OPENAI_API_KEY')
    @classmethod
    def validate_openai_key(cls, v):
        if not v or not v.startswith(("sk-", "org-")):
            raise ValueError("OPENAI_API_KEY must be provided and start with 'sk-' or 'org-'")
        return v
    
    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return v
    
    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator('CHUNK_OVERLAP')
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        # Access other values through info.data
        chunk_size = info.data.get('CHUNK_SIZE', 1000)
        if v >= chunk_size:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    RATE_LIMIT_ENABLED: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"
    )

class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: List[str] = Field(default_factory=list)  # Must be set explicitly
    
    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_production_cors(cls, v):
        if "*" in v:
            raise ValueError("Wildcard CORS origins not allowed in production")
        if not v:
            raise ValueError("CORS_ORIGINS must be explicitly set in production")
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_production_secret(cls, v):
        if v.startswith("test-") or "development" in v.lower():
            raise ValueError("Production SECRET_KEY cannot contain test or development indicators")
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env.production",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"
    )

class TestingSettings(Settings):
    DATABASE_URL: str = "sqlite:///./data/test_database.db"
    CHROMA_DB_PATH: str = "./data/test_chroma_db"
    RATE_LIMIT_ENABLED: bool = False
    OPENAI_API_KEY: str = "sk-test-key-for-testing"
    SECRET_KEY: str = "test-secret-key-for-testing-only-32-characters-minimum"
    
    model_config = SettingsConfigDict(
        env_file=".env.testing",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"
    )

def get_environment_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

# Validation functions
def validate_configuration():
    """Validate configuration on startup"""
    try:
        settings = get_settings()
        
        # Check required directories exist
        os.makedirs(os.path.dirname(settings.UPLOAD_DIR), exist_ok=True)
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        
        # Validate chunk settings
        if settings.CHUNK_OVERLAP >= settings.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        
        # Validate file size
        if settings.MAX_FILE_SIZE > 100 * 1024 * 1024:  # 100MB
            print("WARNING: MAX_FILE_SIZE is very large, consider reducing it")
        
        # Production-specific validations
        if settings.is_production:
            if settings.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if "*" in settings.CORS_ORIGINS:
                raise ValueError("Wildcard CORS not allowed in production")
        
        print(f"Configuration validated for {settings.ENVIRONMENT} environment")
        return True
        
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False

# Configuration summary for debugging
def get_config_summary(settings: Settings) -> dict:
    """Get a safe summary of configuration for logging"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database_type": settings.DATABASE_URL.split("://")[0],
        "openai_model": settings.OPENAI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "allowed_extensions": settings.ALLOWED_FILE_EXTENSIONS,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "log_level": settings.LOG_LEVEL
    }