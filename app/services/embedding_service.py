import google.generativeai as genai
from typing import List
import numpy as np
import os
from dotenv import load_dotenv

class EmbeddingService:
    def __init__(self):
        """
        Initialize Gemini embedding service using API key from .env
        """
        # Load environment variables from .env file
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Please add GEMINI_API_KEY to your .env file.")

        genai.configure(api_key=api_key)
        self.model_name = "models/embedding-001"

    def generate_embedding(self, text: str) -> List[float]:
        """
        Convert text to vector embedding using Gemini
        """
        response = genai.embed_content(
            model=self.model_name,
            content=text
        )
        return response["embedding"]

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts at once
        """
        embeddings = []
        for text in texts:
            response = genai.embed_content(
                model=self.model_name,
                content=text
            )
            embeddings.append(response["embedding"])
        return embeddings

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return float(dot_product / (norm1 * norm2))


# Global instance
embedding_service = EmbeddingService()
