from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryRequest,
    ConversationHistory,
    UserConversationsResponse,
    MessageFeedbackRequest,
    ChatAnalytics
)
from app.services.chat_service import chat_service
from app.models.conversations import Message, Conversation
from app.models.users import User

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to the chatbot and get AI response
    
    - **message**: The user's question or message
    - **user_email**: Email of the user sending the message
    - **session_id**: Optional session ID to continue existing conversation
    """
    
    try:
        response = chat_service.generate_response(
            db=db,
            user_email=request.user_email,
            user_message=request.message,
            session_id=request.session_id
        )
        
        return ChatMessageResponse(**response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )

@router.get("/conversations", response_model=UserConversationsResponse)
async def get_user_conversations(
    user_email: str,
    db: Session = Depends(get_db)
):
    """
    Get list of all conversations for a user
    
    - **user_email**: Email of the user
    """
    
    try:
        conversations = chat_service.list_user_conversations(db, user_email)
        
        return UserConversationsResponse(
            conversations=conversations,
            total_count=len(conversations)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversations: {str(e)}"
        )

@router.post("/history", response_model=ConversationHistory)
async def get_conversation_history(
    request: ChatHistoryRequest,
    db: Session = Depends(get_db)
):
    """
    Get detailed history of a specific conversation
    
    - **user_email**: Email of the user
    - **session_id**: ID of the conversation session
    """
    
    try:
        history = chat_service.get_conversation_history(
            db=db,
            user_email=request.user_email,
            session_id=request.session_id
        )
        
        if "error" in history:
            raise HTTPException(status_code=404, detail=history["error"])
        
        return ConversationHistory(**history)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation history: {str(e)}"
        )

@router.post("/feedback")
async def submit_message_feedback(
    request: MessageFeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit feedback (thumbs up/down) for a bot message
    
    - **message_id**: ID of the message to rate
    - **feedback**: -1 (thumbs down), 0 (neutral), 1 (thumbs up)
    """
    
    try:
        # Find the message
        message = db.query(Message).filter(
            Message.id == request.message_id,
            Message.is_user_message == False  # Only allow feedback on bot messages
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found or not eligible for feedback"
            )
        
        # Update feedback
        message.user_feedback = request.feedback
        db.commit()
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting feedback: {str(e)}"
        )

@router.delete("/conversation/{session_id}")
async def delete_conversation(
    session_id: str,
    user_email: str,
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) a conversation
    
    - **session_id**: ID of the conversation to delete
    - **user_email**: Email of the user (for authorization)
    """
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find conversation
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Soft delete (mark as inactive)
        conversation.is_active = False
        db.commit()
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )

@router.put("/conversation/{session_id}/title")
async def update_conversation_title(
    session_id: str,
    new_title: str,
    user_email: str,
    db: Session = Depends(get_db)
):
    """
    Update the title of a conversation
    
    - **session_id**: ID of the conversation
    - **new_title**: New title for the conversation
    - **user_email**: Email of the user (for authorization)
    """
    
    if len(new_title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find conversation
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user.id,
            Conversation.is_active == True
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update title
        conversation.title = new_title.strip()[:255]  # Limit to 255 chars
        db.commit()
        
        return {"message": "Conversation title updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating conversation title: {str(e)}"
        )

@router.get("/analytics", response_model=ChatAnalytics)
async def get_chat_analytics(
    db: Session = Depends(get_db)
):
    """
    Get analytics about chat usage and performance
    """
    
    try:
        # Total conversations and messages
        total_conversations = db.query(Conversation).filter(
            Conversation.is_active == True
        ).count()
        
        total_messages = db.query(Message).count()
        
        # Average confidence score for bot messages
        avg_confidence = db.query(
            db.func.avg(Message.confidence_score)
        ).filter(
            Message.is_user_message == False,
            Message.confidence_score.isnot(None)
        ).scalar()
        
        # Most active departments (based on document usage)
        # This is a simplified version - you might want more complex analytics
        dept_activity = db.query(
            db.func.count(Message.id).label('count')
        ).filter(
            Message.is_user_message == False
        ).scalar()
        
        return ChatAnalytics(
            total_conversations=total_conversations,
            total_messages=total_messages,
            average_confidence_score=float(avg_confidence) if avg_confidence else None,
            most_active_departments=[
                {"department": "All", "message_count": dept_activity or 0}
            ],
            popular_topics=["General Questions"]  # Placeholder - implement topic analysis
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving analytics: {str(e)}"
        )

@router.post("/start")
async def start_new_conversation(
    user_email: str,
    db: Session = Depends(get_db)
):
    """
    Start a new conversation session
    
    - **user_email**: Email of the user starting the conversation
    """
    
    try:
        import uuid
        
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Create conversation through chat service
        conversation, user = chat_service.get_or_create_conversation(
            db=db,
            user_email=user_email,
            session_id=session_id
        )
        
        return {
            "session_id": conversation.session_id,
            "message": "New conversation started",
            "user_name": user.name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting new conversation: {str(e)}"
        )