from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Conversation metadata
    title = Column(String(255))  # Optional title/summary
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    documents = relationship("ConversationDocument", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    is_user_message = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Bot response metadata (only for bot messages)
    source_documents = Column(JSON)  # List of document IDs used
    confidence_score = Column(Float)  # 0-1 confidence rating
    user_feedback = Column(Integer)  # 1 (thumbs up), -1 (thumbs down), null (no feedback)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

class ConversationDocument(Base):
    __tablename__ = "conversation_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Analytics
    relevance_score = Column(Float)  # How relevant was this document
    used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="documents")
    document = relationship("Document", back_populates="conversations")