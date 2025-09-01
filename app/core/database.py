import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path


# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/database.db")

# Handle both SQLite (local) and PostgreSQL (production)
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration (local development)
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration (production)
    engine = create_engine(DATABASE_URL)
    
# Create SessionLocal class - this handles database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all our models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all database tables (careful!)"""
    Base.metadata.drop_all(bind=engine)