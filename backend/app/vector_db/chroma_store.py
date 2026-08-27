import os
from langchain_chroma import Chroma
from app.embeddings.providers import get_default_embeddings

# Use a persistent directory inside the vector_db folder
PERSIST_DIRECTORY = os.path.join(os.path.dirname(__file__), "chroma_data")

class VectorStoreManager:
    def __init__(self, collection_name: str = "medical_knowledge"):
        self.collection_name = collection_name
        self.embeddings = get_default_embeddings()
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=PERSIST_DIRECTORY
        )

    def add_documents(self, documents, ids=None):
        """Add documents to the vector store."""
        if documents:
            if ids:
                self.vector_store.add_documents(documents, ids=ids)
            else:
                self.vector_store.add_documents(documents)
            print(f"Added {len(documents)} document chunks to Vector DB.")
        
    def similarity_search(self, query: str, k: int = 4):
        """Basic semantic search."""
        return self.vector_store.similarity_search(query, k=k)

    def max_marginal_relevance_search(self, query: str, k: int = 4, fetch_k: int = 20):
        """MMR search to optimize for relevance and diversity."""
        return self.vector_store.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k)

# Global instance for easy access
_vector_db_manager = None

def get_vector_db_manager():
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorStoreManager()
    return _vector_db_manager
