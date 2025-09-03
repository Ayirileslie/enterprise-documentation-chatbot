# recreate_database.py - Fix schema mismatch
import os
from pathlib import Path
from app.core.database import engine, Base

def recreate_database():
    """Drop and recreate all tables with new schema"""
    
    print("Recreating database with updated schema...")
    
    # Import all models to register them
    from app.models import users, auth, documents, conversations
    
    # Drop all existing tables
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables with new schema
    print("Creating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    
    print("Database recreated successfully!")
    print("Note: All existing data has been deleted.")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"Tables created: {tables}")
    
    # Check User table columns
    if 'users' in tables:
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        print(f"User table columns: {column_names}")

if __name__ == "__main__":
    confirm = input("This will delete all existing data. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        recreate_database()
    else:
        print("Operation cancelled.")