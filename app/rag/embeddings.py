import os
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings
from app.core.logging import logger

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        pass


class FastEmbedProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-small-en"):
        self._model_name = model_name
        self._embedding_model = None
        if TextEmbedding is not None:
            try:
                logger.info(f"Loading FastEmbed model: {model_name}")
                self._embedding_model = TextEmbedding(model_name=model_name)
            except Exception as e:
                logger.warning(f"Could not load FastEmbed {model_name}: {e}. Fallback enabled.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._embedding_model:
            try:
                embeddings = list(self._embedding_model.embed(texts))
                return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings]
            except Exception as e:
                logger.error(f"FastEmbed batch failed: {e}")
        # Fallback to deterministic normalized hash vector
        return [self._hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    @property
    def model_version(self) -> str:
        return f"fastembed-{self._model_name}"

    def _hash_vector(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic 384-dim pseudo-semantic embedding fallback based on n-gram hashes."""
        vec = [0.0] * dim
        tokens = text.lower().split()
        if not tokens:
            return vec
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dim: int = 384):
        self._dim = dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            vec = [0.0] * self._dim
            tokens = text.lower().split()
            for token in tokens:
                h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dim
                vec[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            results.append([x / norm for x in vec])
        return results

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    @property
    def model_version(self) -> str:
        return "mock-deterministic-384"


def get_embedding_provider() -> BaseEmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "fastembed" and TextEmbedding is not None:
        return FastEmbedProvider(model_name=settings.EMBEDDING_MODEL)
    return MockEmbeddingProvider()
