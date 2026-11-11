import os
import gc
import math
import hashlib
import threading
from abc import ABC, abstractmethod
from typing import List, Optional
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
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en",
        cache_dir: Optional[str] = None
    ):
        self._model_name = model_name
        self._cache_dir = cache_dir or settings.FASTEMBED_CACHE_PATH
        self._embedding_model = None
        self._model_lock = threading.Lock()
        logger.info(
            f"Registered shared FastEmbed provider for '{model_name}' "
            f"(lazy loading enabled, cache_dir='{self._cache_dir}')."
        )

    def _get_model(self):
        """Thread-safe lazy initializer for the underlying ONNX TextEmbedding model."""
        if self._embedding_model is None and TextEmbedding is not None:
            with self._model_lock:
                if self._embedding_model is None:
                    try:
                        logger.info(
                            f"[EMBEDDING INIT] Loading shared FastEmbed model: {self._model_name} "
                            f"(threads=1, cache_dir={self._cache_dir})..."
                        )
                        # Set threads=1 to avoid large thread pool overhead in 512MB RAM environments
                        self._embedding_model = TextEmbedding(
                            model_name=self._model_name,
                            cache_dir=self._cache_dir,
                            threads=1
                        )
                        logger.info(f"[EMBEDDING READY] FastEmbed model '{self._model_name}' loaded successfully.")
                    except Exception as e:
                        logger.warning(f"Could not load FastEmbed {self._model_name}: {e}. Deterministic fallback active.")
        return self._embedding_model

    @property
    def is_loaded(self) -> bool:
        return self._embedding_model is not None

    def warmup(self) -> None:
        """Explicit warmup to verify model readiness and run immediate garbage collection."""
        model = self._get_model()
        if model is not None:
            try:
                _ = list(model.embed(["startup warmup probe"]))
                gc.collect()
                logger.info(f"[EMBEDDING WARMUP] Model '{self._model_name}' primed and ready.")
            except Exception as e:
                logger.warning(f"Model warmup warning: {e}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        if model:
            try:
                embeddings = list(model.embed(texts))
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


# Thread-safe global singleton
_EMBEDDING_PROVIDER_INSTANCE: Optional[BaseEmbeddingProvider] = None
_EMBEDDING_LOCK = threading.Lock()


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Returns the shared application-wide embedding provider singleton."""
    global _EMBEDDING_PROVIDER_INSTANCE
    if _EMBEDDING_PROVIDER_INSTANCE is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_PROVIDER_INSTANCE is None:
                if settings.EMBEDDING_PROVIDER == "fastembed" and TextEmbedding is not None:
                    _EMBEDDING_PROVIDER_INSTANCE = FastEmbedProvider(
                        model_name=settings.EMBEDDING_MODEL,
                        cache_dir=settings.FASTEMBED_CACHE_PATH
                    )
                else:
                    _EMBEDDING_PROVIDER_INSTANCE = MockEmbeddingProvider()
    return _EMBEDDING_PROVIDER_INSTANCE
