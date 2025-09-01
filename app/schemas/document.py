from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Request schemas (what users send to API)
class DocumentUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=100)
    content_type: str = Field(..., pattern="^(policy|manual|wiki|procedure|guide)$")
    uploaded_by: str = Field(..., min_length=1, max_length=255)

class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    department: Optional[str] = None
    content_type: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)

# Response schemas (what API returns to users)
class DocumentChunkResponse(BaseModel):
    id: int
    content: str
    chunk_index: int
    relevance_score: Optional[float] = None

class DocumentResponse(BaseModel):
    id: int
    title: str
    department: str
    content_type: str
    file_size: int
    original_filename: str
    uploaded_by: str
    uploaded_at: datetime
    is_active: bool

    model_config = {
        "from_attributes": True  # replaces Config class in Pydantic v2
    }

class DocumentSearchResponse(BaseModel):
    documents: List[DocumentResponse]
    chunks: List[DocumentChunkResponse]
    total_results: int
    query: str

class DocumentUploadResponse(BaseModel):
    id: int
    title: str
    message: str
    chunks_created: int
