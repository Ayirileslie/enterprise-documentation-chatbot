from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

def test_embeddings():
    """Test embedding generation"""
    text1 = "Remote work policy allows working from home"
    text2 = "Employees can work remotely from their house"
    text3 = "Coffee machine maintenance schedule"
    
    # Generate embeddings
    emb1 = embedding_service.generate_embedding(text1)
    emb2 = embedding_service.generate_embedding(text2)
    emb3 = embedding_service.generate_embedding(text3)
    
    # Test similarity
    sim_12 = embedding_service.calculate_similarity(emb1, emb2)
    sim_13 = embedding_service.calculate_similarity(emb1, emb3)
    
    print(f"Similarity between remote work texts: {sim_12:.3f}")
    print(f"Similarity between remote work and coffee: {sim_13:.3f}")
    
    # Should show: remote work texts are more similar than unrelated text

if __name__ == "__main__":
    test_embeddings()