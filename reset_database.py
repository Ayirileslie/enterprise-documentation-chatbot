from app.services.vector_service import vector_service
from app.core.database import SessionLocal
from app.models.documents import Document

def reset_everything():
    # Reset ChromaDB collection
    vector_service.reset_collection()
    
    # Optionally reset your SQL database documents table
    db = SessionLocal()
    try:
        # Delete all documents from SQL database if you want a fresh start
        db.query(Document).delete()
        db.commit()
        print("Cleared SQL database")
    except Exception as e:
        print(f"Error clearing SQL database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_everything()