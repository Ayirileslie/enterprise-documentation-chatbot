# create_db.py
from app.core.database import Base, engine
from app.models import users, documents, conversations  # import models so they're registered

def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!")
