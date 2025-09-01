from app.core.database import SessionLocal, create_tables
from app.models.users import User
from app.models.documents import Document
from app.models.conversations import Conversation, Message

def test_basic_operations():
    # Create tables first
    create_tables()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Create a test user
        user = User(
            name="John Doe",
            email="john@company.com",
            department="Engineering"
        )
        db.add(user)
        db.commit()
        db.refresh(user)  # Get the assigned ID
        
        print(f"Created user: {user.name} with ID {user.id}")
        
        # Create a test document
        doc = Document(
            title="API Guidelines",
            file_path="/docs/api_guidelines.pdf",
            department="Engineering", 
            content_type="manual",
            uploaded_by="admin@company.com"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        print(f"Created document: {doc.title} with ID {doc.id}")
        
        # Query test
        users = db.query(User).all()
        print(f"Total users in database: {len(users)}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_basic_operations()