import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Any, List
from pydantic import Field

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseRetriever, Document as LangChainDocument
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from app.models.conversations import Conversation, Message
from app.models.users import User
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

class CustomDocumentRetriever(BaseRetriever):
    """Custom retriever that uses ChromaDB vector service"""

    vector_service: Any = Field(...)
    embedding_service: Any = Field(...)
    top_k: int = Field(default=4)

    def _get_relevant_documents(self, query: str) -> List[LangChainDocument]:
        """Retrieve relevant documents for the query"""
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query)

        # Search vector database
        results = self.vector_service.search_similar_chunks(
            query_embedding=query_embedding,
            n_results=self.top_k
        )

        # Convert to LangChain Document format
        documents = []
        for i, (content, distance, metadata) in enumerate(zip(
            results["documents"],
            results["distances"],
            results["metadatas"]
        )):
            doc = LangChainDocument(
                page_content=content,
                metadata={
                    "source": metadata.get("title", "Unknown Document"),
                    "department": metadata.get("department", ""),
                    "content_type": metadata.get("content_type", ""),
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index", i),
                    "raw_distance": distance,
                    "relevance_score": 1 - distance  # adjust if cosine sim is used
                }
            )
            documents.append(doc)

        return documents
    
class ChatService:
    def __init__(self):
        # Initialize OpenAI
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.1,  # Low temperature for consistent, factual responses
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create custom retriever
        self.retriever = CustomDocumentRetriever(
                vector_service=vector_service,
                embedding_service=embedding_service,
                top_k=4
            )

        
        # Create conversation memory
        self.memory = ConversationBufferWindowMemory(
            k=5,  # Remember last 5 exchanges
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Custom prompt template for company chatbot
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""You are a helpful AI assistant for company employees. Use the provided context from company documents to answer questions accurately and helpfully.

Context from company documents:
{context}

Chat History:
{chat_history}

Instructions:
1. Answer based primarily on the provided context
2. If the context doesn't contain relevant information, say so clearly
3. Always be professional and helpful
4. Cite specific documents when possible
5. If asked about something not in company docs, politely redirect to appropriate resources

Question: {question}

Answer:"""
        )
        
        # Create the conversational retrieval chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": self.prompt_template}
        )
    
    def get_or_create_conversation(
        self, 
        db: Session, 
        user_email: str, 
        session_id: Optional[str] = None
    ) -> Tuple[Conversation, User]:
        """Get existing conversation or create new one"""
        
        # Get or create user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                name=user_email.split("@")[0],  # Use email prefix as name
                email=user_email,
                role="employee"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Get or create conversation
        conversation = None
        if session_id:
            conversation = db.query(Conversation).filter(
                Conversation.session_id == session_id,
                Conversation.user_id == user.id,
                Conversation.is_active == True
            ).first()
        
        if not conversation:
            # Create new conversation
            import uuid
            conversation = Conversation(
                user_id=user.id,
                session_id=session_id or str(uuid.uuid4()),
                title="New Chat",
                is_active=True
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        return conversation, user
    
    def save_message(
        self, 
        db: Session, 
        conversation: Conversation, 
        content: str, 
        is_user_message: bool,
        source_documents: Optional[List[Dict]] = None,
        confidence_score: Optional[float] = None
    ) -> Message:
        """Save a message to the database"""
        
        message = Message(
            conversation_id=conversation.id,
            content=content,
            is_user_message=is_user_message,
            source_documents=source_documents,
            confidence_score=confidence_score
        )
        
        db.add(message)
        
        # Update conversation timestamp
        conversation.last_message_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message
    
    def load_conversation_history(self, db: Session, conversation: Conversation):
        """Load previous messages into memory"""
        
        # Clear existing memory
        self.memory.clear()
        
        # Get recent messages (last 10 messages or 5 exchanges)
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.timestamp).limit(10).all()
        
        # Add messages to memory in chronological order
        for message in messages:
            if message.is_user_message:
                self.memory.chat_memory.add_user_message(message.content)
            else:
                self.memory.chat_memory.add_ai_message(message.content)
    
    def generate_response(
        self, 
        db: Session,
        user_email: str,
        user_message: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """Generate AI response to user message"""
        
        try:
            # Get or create conversation
            conversation, user = self.get_or_create_conversation(
                db, user_email, session_id
            )
            
            # Load conversation history
            self.load_conversation_history(db, conversation)
            
            # Save user message
            user_msg = self.save_message(
                db, conversation, user_message, is_user_message=True
            )
            
            # Generate AI response
            result = self.chain({"question": user_message})
            
            ai_response = result["answer"]
            source_docs = result["source_documents"]
            
            # Process source documents for storage
            source_doc_info = []
            for doc in source_docs:
                source_doc_info.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "department": doc.metadata.get("department", ""),
                    "content_type": doc.metadata.get("content_type", ""),
                    "document_id": doc.metadata.get("document_id"),
                    "relevance_score": doc.metadata.get("relevance_score", 0),
                    "chunk_content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                })
            
            # Calculate confidence score based on relevance of sources
            confidence_score = None
            if source_doc_info:
                avg_relevance = sum(doc.get("relevance_score", 0) for doc in source_doc_info) / len(source_doc_info)
                confidence_score = min(avg_relevance, 1.0)  # Cap at 1.0
            
            # Save AI response
            ai_msg = self.save_message(
                db, 
                conversation, 
                ai_response, 
                is_user_message=False,
                source_documents=source_doc_info,
                confidence_score=confidence_score
            )
            
            # Update conversation title if it's the first exchange
            if conversation.title == "New Chat" and len(user_message) > 10:
                # Generate a title from the first user message
                conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")
                db.commit()
            
            return {
                "response": ai_response,
                "session_id": conversation.session_id,
                "message_id": ai_msg.id,
                "sources": source_doc_info,
                "confidence_score": confidence_score,
                "conversation_title": conversation.title
            }
            
        except Exception as e:
            # Handle errors gracefully
            return {
                "response": f"I apologize, but I encountered an error while processing your request: {str(e)}",
                "session_id": session_id,
                "message_id": None,
                "sources": [],
                "confidence_score": None,
                "error": str(e)
            }
    
    def get_conversation_history(
        self, 
        db: Session, 
        user_email: str, 
        session_id: str
    ) -> Dict:
        """Get conversation history"""
        
        # Find user and conversation
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return {"error": "User not found"}
        
        conversation = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        # Get messages
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.timestamp).all()
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg.id,
                "content": msg.content,
                "is_user_message": msg.is_user_message,
                "timestamp": msg.timestamp.isoformat(),
                "sources": msg.source_documents,
                "confidence_score": msg.confidence_score
            })
        
        return {
            "session_id": conversation.session_id,
            "title": conversation.title,
            "messages": formatted_messages,
            "started_at": conversation.started_at.isoformat(),
            "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None
        }
    
    def list_user_conversations(self, db: Session, user_email: str) -> List[Dict]:
        """Get list of user's conversations"""
        
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return []
        
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user.id,
            Conversation.is_active == True
        ).order_by(Conversation.last_message_at.desc()).all()
        
        result = []
        for conv in conversations:
            # Get message count
            msg_count = db.query(Message).filter(
                Message.conversation_id == conv.id
            ).count()
            
            result.append({
                "session_id": conv.session_id,
                "title": conv.title,
                "started_at": conv.started_at.isoformat(),
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "message_count": msg_count
            })
        
        return result

# Global instance
chat_service = ChatService()