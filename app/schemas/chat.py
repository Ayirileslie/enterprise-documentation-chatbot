from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request schemas
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_email: EmailStr  # ✅ replaced regex with EmailStr
    session_id: Optional[str] = None

class ChatHistoryRequest(BaseModel):
    user_email: EmailStr  # ✅ replaced regex with EmailStr
    session_id: str

class MessageFeedbackRequest(BaseModel):
    message_id: int
    feedback: int = Field(..., ge=-1, le=1)  # -1 (bad), 0 (neutral), 1 (good)

# Response schemas
class SourceDocument(BaseModel):
    source: str
    department: str
    content_type: str
    document_id: Optional[int]
    relevance_score: float
    chunk_content: str

class ChatMessageResponse(BaseModel):
    response: str
    session_id: str
    message_id: Optional[int]
    sources: List[SourceDocument]
    confidence_score: Optional[float]
    conversation_title: str
    error: Optional[str] = None

class MessageHistoryItem(BaseModel):
    id: int
    content: str
    is_user_message: bool
    timestamp: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    user_feedback: Optional[int] = None

class ConversationHistory(BaseModel):
    session_id: str
    title: str
    messages: List[MessageHistoryItem]
    started_at: str
    last_message_at: Optional[str]

class ConversationSummary(BaseModel):
    session_id: str
    title: str
    started_at: str
    last_message_at: Optional[str]
    message_count: int

class UserConversationsResponse(BaseModel):
    conversations: List[ConversationSummary]
    total_count: int

# Analytics schemas
class ChatAnalytics(BaseModel):
    total_conversations: int
    total_messages: int
    average_confidence_score: Optional[float]
    most_active_departments: List[Dict[str, Any]]
    popular_topics: List[str]
