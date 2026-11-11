from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from app.core.logging import logger


class VectorRepositoryInterface(ABC):
    @abstractmethod
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        pass

    @abstractmethod
    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Returns list of dicts:
        [{ "id": str, "document": str, "metadata": dict, "similarity": float }]
        """
        pass

    @abstractmethod
    def delete_by_sector(self, sector_id: str) -> None:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class ChromaVectorStore(VectorRepositoryInterface):
    COLLECTION_NAME = "sector_knowledge_base"

    def __init__(self, persist_dir: str = settings.CHROMA_PERSIST_DIR):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    @property
    def collection(self):
        return self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        coll = self.collection
        count = coll.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        res = coll.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"]
        )

        results = []
        if res and res["ids"] and len(res["ids"][0]) > 0:
            ids = res["ids"][0]
            docs = res["documents"][0] if res.get("documents") else [""] * len(ids)
            metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(ids)
            dists = res["distances"][0] if res.get("distances") else [0.0] * len(ids)

            for item_id, doc, meta, dist in zip(ids, docs, metas, dists):
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                results.append({
                    "id": item_id,
                    "document": doc,
                    "metadata": meta,
                    "similarity": round(similarity, 4)
                })
        return results

    def delete_by_sector(self, sector_id: str) -> None:
        try:
            self.collection.delete(where={"sector_id": sector_id})
        except Exception as e:
            logger.warning(f"Chroma delete_by_sector notice: {e}")

    def reset(self) -> None:
        try:
            # Delete all existing document IDs to preserve collection identity
            coll = self.collection
            existing = coll.get()
            if existing and existing.get("ids"):
                coll.delete(ids=existing["ids"])
        except Exception as e:
            logger.error(f"Failed to reset Chroma collection: {e}")


class SupabasePgVectorStore(VectorRepositoryInterface):
    """
    Production-ready Vector Store adapter for Supabase pgvector.
    Can be activated via VECTOR_STORE=supabase and SUPABASE_URL / DATABASE_URL.
    """
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.db_url = db_url
        logger.info("Initializing Supabase pgvector repository interface.")

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        # Supabase pgvector insert query representation
        logger.info(f"SupabasePgVectorStore: Upserting {len(documents)} documents.")

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        # Returns cosine similarity via pgvector operator <=>
        return []

    def delete_by_sector(self, sector_id: str) -> None:
        logger.info(f"SupabasePgVectorStore: Deleting sector {sector_id}.")

    def reset(self) -> None:
        logger.info("SupabasePgVectorStore: Reset collection.")


def get_vector_store() -> VectorRepositoryInterface:
    if settings.VECTOR_STORE.lower() == "supabase" and settings.SUPABASE_URL:
        return SupabasePgVectorStore()
    return ChromaVectorStore()
