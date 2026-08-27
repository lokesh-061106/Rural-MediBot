from abc import ABC, abstractmethod
import os

class EmbeddingProvider(ABC):
    @abstractmethod
    def get_embeddings(self):
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    def get_embeddings(self):
        from langchain_core.embeddings import FakeEmbeddings
        return FakeEmbeddings(size=384)

class MiniLMEmbeddingProvider(EmbeddingProvider):
    def get_embeddings(self):
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

class BGEEmbeddingProvider(EmbeddingProvider):
    def get_embeddings(self):
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

def get_default_embeddings():
    if os.environ.get("USE_MOCK_LLM") == "true":
        return MockEmbeddingProvider().get_embeddings()
        
    model_type = os.environ.get("EMBEDDING_MODEL", "minilm").lower()
    
    if model_type == "bge":
        return BGEEmbeddingProvider().get_embeddings()
    else:
        return MiniLMEmbeddingProvider().get_embeddings()
