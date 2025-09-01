from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    # Primary key - unique identifier
    id = Column(Integer, primary_key=True, index=True)
    
    # Document information
    title = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    department = Column(String(100), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # "policy", "manual", etc.
    
    # File metadata  
    file_size = Column(Integer)  # in bytes
    original_filename = Column(String(255))
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    last_modified = Column(DateTime(timezone=True), onupdate=func.now())
    
    # User who uploaded
    uploaded_by = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships to other tables
    chunks = relationship("DocumentChunk", back_populates="document")
    conversations = relationship("ConversationDocument", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Chunk content and metadata
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # 0, 1, 2...
    start_char = Column(Integer)  # Position in original document
    end_char = Column(Integer)
    
    # Reference to vector embedding
    vector_id = Column(String(100))  # ChromaDB ID
    
    # Relationship back to document
    document = relationship("Document", back_populates="chunks")