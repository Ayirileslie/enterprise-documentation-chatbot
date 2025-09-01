from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.documents import Document, DocumentChunk
from app.schemas.document import (
    DocumentUploadResponse, 
    DocumentSearchRequest, 
    DocumentSearchResponse,
    DocumentResponse
)
from app.services.document_service import document_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    department: str = Form(...),
    content_type: str = Form(...),
    uploaded_by: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a new document
    
    - **file**: The document file (PDF, DOCX, TXT, MD)
    - **title**: Human-readable title for the document
    - **department**: Department that owns this document
    - **content_type**: Type of document (policy, manual, wiki, etc.)
    - **uploaded_by**: Email/name of person uploading
    """
    
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt", ".md"}
    file_extension = None
    if file.filename:
        file_extension = "." + file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {allowed_extensions}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Process document through the complete pipeline
        document = await document_service.process_document(
            db=db,
            file_content=file_content,
            filename=file.filename,
            title=title,
            department=department,
            content_type=content_type,
            uploaded_by=uploaded_by
        )
        
        # Count chunks created
        chunks_count = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).count()
        
        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            message="Document uploaded and processed successfully",
            chunks_created=chunks_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_request: DocumentSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search documents using semantic similarity
    
    - **query**: What you're looking for (e.g., "remote work policy")
    - **department**: Optional filter by department
    - **content_type**: Optional filter by document type
    - **limit**: Maximum number of results to return
    """
    
    try:
        # Generate embedding for the search query
        query_embedding = embedding_service.generate_embedding(search_request.query)
        
        # Search for similar chunks in vector database
        vector_results = vector_service.search_similar_chunks(
            query_embedding=query_embedding,
            n_results=search_request.limit * 2  # Get more to allow filtering
        )
        
        # Extract document IDs and chunk info from vector results
        chunk_results = []
        document_ids = set()
        
        for i, (doc_text, distance, metadata, chunk_id) in enumerate(zip(
            vector_results["documents"],
            vector_results["distances"], 
            vector_results["metadatas"],
            vector_results["ids"]
        )):
            # Convert distance to similarity score (higher = more similar)
            relevance_score = 1 - distance
            
            # Apply filters if specified
            if search_request.department and metadata.get("department") != search_request.department:
                continue
            if search_request.content_type and metadata.get("content_type") != search_request.content_type:
                continue
            
            chunk_results.append({
                "content": doc_text,
                "chunk_index": metadata.get("chunk_index", 0),
                "relevance_score": relevance_score,
                "document_id": metadata.get("document_id"),
                "vector_id": chunk_id
            })
            
            document_ids.add(metadata.get("document_id"))
            
            if len(chunk_results) >= search_request.limit:
                break
        
        # Get full document information from SQL database
        documents = []
        if document_ids:
            documents_query = db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.is_active == True
            )
            documents = documents_query.all()
        
        return DocumentSearchResponse(
            documents=[DocumentResponse.from_orm(doc) for doc in documents],
            chunks=chunk_results,
            total_results=len(chunk_results),
            query=search_request.query
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    department: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all documents with optional filtering
    
    - **department**: Filter by department
    - **content_type**: Filter by document type
    - **limit**: Number of documents to return
    - **offset**: Number of documents to skip (for pagination)
    """
    
    query = db.query(Document).filter(Document.is_active == True)
    
    # Apply filters
    if department:
        query = query.filter(Document.department == department)
    if content_type:
        query = query.filter(Document.content_type == content_type)
    
    # Apply pagination
    documents = query.offset(offset).limit(limit).all()
    
    return [DocumentResponse.from_orm(doc) for doc in documents]

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific document
    """
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.from_orm(document)

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all its chunks
    """
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete vector embeddings
        vector_service.delete_document_chunks(document_id)
        
        # Soft delete in SQL (mark as inactive)
        document.is_active = False
        db.commit()
        
        return {"message": f"Document '{document.title}' deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/stats/overview")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get system statistics
    """
    
    total_documents = db.query(Document).filter(Document.is_active == True).count()
    total_chunks = db.query(DocumentChunk).count()
    vector_stats = vector_service.get_collection_stats()
    
    # Get documents by department
    dept_stats = db.query(Document.department, db.func.count(Document.id)).filter(
        Document.is_active == True
    ).group_by(Document.department).all()
    
    return {
        "total_documents": total_documents,
        "total_chunks": total_chunks,
        "vector_chunks": vector_stats["total_chunks"],
        "departments": dict(dept_stats)
    }