from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import json
import math
import threading
from sqlalchemy import text
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

    @abstractmethod
    def count(self) -> int:
        pass


class ChromaVectorStore(VectorRepositoryInterface):
    COLLECTION_NAME = "sector_knowledge_base"

    def __init__(self, persist_dir: str = settings.CHROMA_PERSIST_DIR):
        self.persist_dir = persist_dir
        try:
            os.makedirs(persist_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.warning(f"Chroma persist_dir '{persist_dir}' not writable: {e}. Falling back to ephemeral /tmp/chroma.")
            self.persist_dir = "/tmp/chroma"
            os.makedirs(self.persist_dir, exist_ok=True)

        logger.info(f"Initializing ChromaVectorStore client at persist_dir: '{self.persist_dir}'")
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )


    @property
    def collection(self):
        return self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as e:
            logger.warning(f"Chroma count error: {e}")
            return 0

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
    Production-ready Vector Store adapter for Supabase / PostgreSQL pgvector.
    Supports native vector(384) cosine distance indexing (<=>) and idempotent upserts.
    Includes in-memory/sqlite cosine distance emulation for local and test environments.
    """
    TABLE_NAME = "sector_embeddings"

    def __init__(self, engine=None):
        from app.db.session import engine as default_engine
        self.engine = engine or default_engine
        self._table_initialized = False
        self._init_lock = threading.Lock()
        logger.info("Initializing Supabase pgvector repository interface.")

    def _ensure_schema(self):
        """Ensures pgvector extension and sector_embeddings table exist idempotently."""
        if self._table_initialized:
            return
        with self._init_lock:
            if self._table_initialized:
                return

            dialect = self.engine.dialect.name
            with self.engine.begin() as conn:
                if dialect == "postgresql":
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    except Exception as e:
                        logger.warning(f"Notice enabling vector extension: {e}")

                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                            id VARCHAR(100) PRIMARY KEY,
                            sector_id VARCHAR(50) NOT NULL,
                            document TEXT NOT NULL,
                            metadata JSONB NOT NULL,
                            embedding vector(384) NOT NULL
                        );
                    """))
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_sector_id 
                        ON {self.TABLE_NAME} (sector_id);
                    """))
                else:
                    # SQLite test fallback
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                            id VARCHAR(100) PRIMARY KEY,
                            sector_id VARCHAR(50) NOT NULL,
                            document TEXT NOT NULL,
                            metadata TEXT NOT NULL,
                            embedding TEXT NOT NULL
                        );
                    """))
            self._table_initialized = True
            logger.info("Supabase pgvector schema verification completed.")

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        self._ensure_schema()
        dialect = self.engine.dialect.name

        with self.engine.begin() as conn:
            for doc, meta, doc_id, emb in zip(documents, metadatas, ids, embeddings):
                sector_id = meta.get("sector_id", "")
                meta_json = json.dumps(meta)
                emb_str = f"[{','.join(f'{x:.6f}' for x in emb)}]"

                if dialect == "postgresql":
                    stmt = text(f"""
                        INSERT INTO {self.TABLE_NAME} (id, sector_id, document, metadata, embedding)
                        VALUES (:id, :sector_id, :document, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                        ON CONFLICT (id) DO UPDATE SET
                            sector_id = EXCLUDED.sector_id,
                            document = EXCLUDED.document,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding;
                    """)
                    conn.execute(stmt, {
                        "id": doc_id,
                        "sector_id": sector_id,
                        "document": doc,
                        "metadata": meta_json,
                        "embedding": emb_str
                    })
                else:
                    # SQLite fallback
                    stmt = text(f"""
                        INSERT OR REPLACE INTO {self.TABLE_NAME} (id, sector_id, document, metadata, embedding)
                        VALUES (:id, :sector_id, :document, :metadata, :embedding)
                    """)
                    conn.execute(stmt, {
                        "id": doc_id,
                        "sector_id": sector_id,
                        "document": doc,
                        "metadata": meta_json,
                        "embedding": emb_str
                    })
        logger.info(f"SupabasePgVectorStore: Upserted {len(documents)} sector chunks into {self.TABLE_NAME}.")

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        self._ensure_schema()
        dialect = self.engine.dialect.name
        emb_str = f"[{','.join(f'{x:.6f}' for x in query_embedding)}]"

        with self.engine.connect() as conn:
            if dialect == "postgresql":
                stmt = text(f"""
                    SELECT id, document, metadata, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM {self.TABLE_NAME}
                    ORDER BY embedding <=> CAST(:query_embedding AS vector) ASC
                    LIMIT :top_k;
                """)
                rows = conn.execute(stmt, {
                    "query_embedding": emb_str,
                    "top_k": top_k
                }).fetchall()

                results = []
                for row in rows:
                    meta = row[2]
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except Exception:
                            meta = {}
                    sim = round(max(0.0, min(1.0, float(row[3]))), 4)
                    results.append({
                        "id": str(row[0]),
                        "document": str(row[1]),
                        "metadata": meta,
                        "similarity": sim
                    })
                return results
            else:
                # SQLite cosine distance fallback
                stmt = text(f"SELECT id, document, metadata, embedding FROM {self.TABLE_NAME}")
                rows = conn.execute(stmt).fetchall()
                if not rows:
                    return []

                scored = []
                for row in rows:
                    meta = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                    emb = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                    # Compute cosine similarity
                    dot = sum(a * b for a, b in zip(query_embedding, emb))
                    norm_a = math.sqrt(sum(a * a for a in query_embedding)) or 1.0
                    norm_b = math.sqrt(sum(b * b for b in emb)) or 1.0
                    cos_sim = round(max(0.0, min(1.0, dot / (norm_a * norm_b))), 4)
                    scored.append({
                        "id": str(row[0]),
                        "document": str(row[1]),
                        "metadata": meta,
                        "similarity": cos_sim
                    })
                scored.sort(key=lambda x: x["similarity"], reverse=True)
                return scored[:top_k]

    def delete_by_sector(self, sector_id: str) -> None:
        self._ensure_schema()
        with self.engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {self.TABLE_NAME} WHERE sector_id = :sector_id"),
                {"sector_id": sector_id}
            )
        logger.info(f"SupabasePgVectorStore: Deleted chunks for sector '{sector_id}'.")

    def reset(self) -> None:
        self._ensure_schema()
        with self.engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {self.TABLE_NAME}"))
        logger.info(f"SupabasePgVectorStore: Reset table {self.TABLE_NAME}.")

    def count(self) -> int:
        try:
            self._ensure_schema()
            with self.engine.connect() as conn:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")).scalar()
                return int(res or 0)
        except Exception as e:
            logger.warning(f"SupabasePgVectorStore count error: {e}")
            return 0


# Thread-safe global singleton
_VECTOR_STORE_INSTANCE: Optional[VectorRepositoryInterface] = None
_VECTOR_STORE_LOCK = threading.Lock()


def get_vector_store() -> VectorRepositoryInterface:
    """Returns the shared application-wide vector repository singleton."""
    global _VECTOR_STORE_INSTANCE
    if _VECTOR_STORE_INSTANCE is None:
        with _VECTOR_STORE_LOCK:
            if _VECTOR_STORE_INSTANCE is None:
                provider = (settings.VECTOR_STORE or "").lower()
                if provider in ("supabase", "pgvector") or (settings.is_production and not settings.DATABASE_URL.startswith("sqlite")):
                    _VECTOR_STORE_INSTANCE = SupabasePgVectorStore()
                else:
                    _VECTOR_STORE_INSTANCE = ChromaVectorStore(persist_dir=settings.CHROMA_PERSIST_DIR)
    return _VECTOR_STORE_INSTANCE

