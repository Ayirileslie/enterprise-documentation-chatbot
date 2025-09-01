import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import uuid
from pathlib import Path

class VectorService:
    def __init__(self):
        # Persistent ChromaDB storage path
        db_path = Path("data/chroma_db")
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection_name = "company_documents"
        # Create or get the documents collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Company documentation embeddings"}
        )

    def reset_collection(self):
        """
        Delete and recreate the entire ChromaDB collection.
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Company documentation embeddings"}
            )
            print(f"Collection '{self.collection_name}' has been reset.")
        except Exception as e:
            print(f"Error resetting collection: {e}")
    
    def add_document_chunk(
        self, 
        chunk_text: str, 
        embedding: List[float],
        metadata: Dict,
        chunk_id: Optional[str] = None
    ) -> str:
        if chunk_id is None:
            chunk_id = str(uuid.uuid4())
        
        self.collection.add(
            documents=[chunk_text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[chunk_id]
        )
        return chunk_id
    
    def search_similar_chunks(
        self, 
        query_embedding: List[float], 
        n_results: int = 5
    ) -> Dict:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return {
            "documents": results["documents"][0],
            "distances": results["distances"][0],
            "metadatas": results["metadatas"][0],
            "ids": results["ids"][0]
        }
    
    def delete_document_chunks(self, document_id: int):
        results = self.collection.get(where={"document_id": document_id})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def get_collection_stats(self) -> Dict:
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection.name
        }

# Global instance
vector_service = VectorService()
