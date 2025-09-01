# Replace the current content with this specific import structure
from app.models.documents import Document, DocumentChunk
from app.models.users import User  
from app.models.conversations import Conversation, Message, ConversationDocument

# Make sure each model is only imported once
__all__ = ["Document", "DocumentChunk", "User", "Conversation", "Message", "ConversationDocument"]