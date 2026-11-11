import gc
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Sector
from app.db.session import SessionLocal
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store
from app.core.logging import logger


class SectorKnowledgeIndexer:
    def __init__(self, vector_store=None, embedding_provider=None):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def reindex_all_sectors(self, db: Optional[Session] = None, force: bool = False) -> int:
        """
        Clears and re-indexes all active sectors from database into vector store.
        If force=False and vector store already contains chunks, skips redundant embedding.
        Each sector produces 3 distinct chunks: Description, Keywords, Examples.
        """
        existing_count = self.vector_store.count()
        if not force and existing_count >= 39:
            logger.info(
                f"[VECTOR STORE READY] Vector store already contains {existing_count} indexed chunks. "
                f"Skipping redundant re-indexing on startup."
            )
            return existing_count

        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            sectors = db.query(Sector).filter(Sector.active == True).all()
            logger.info(f"Re-indexing {len(sectors)} active sectors into vector store...")

            self.vector_store.reset()

            documents = []
            metadatas = []
            ids = []

            for s in sectors:
                # 1. Description Chunk
                desc_doc = (
                    f"Sector: {s.name}\n"
                    f"Description: {s.description}\n"
                    f"Disambiguation: {s.notes or ''}"
                )
                documents.append(desc_doc)
                metadatas.append({
                    "sector_id": s.id,
                    "sector_name": s.name,
                    "chunk_type": "description"
                })
                ids.append(f"{s.id}_description")

                # 2. Keywords Chunk
                kw_list = s.keywords if isinstance(s.keywords, list) else []
                kw_str = ", ".join(kw_list)
                kw_doc = (
                    f"Sector: {s.name}\n"
                    f"Core Industry Keywords: {kw_str}"
                )
                documents.append(kw_doc)
                metadatas.append({
                    "sector_id": s.id,
                    "sector_name": s.name,
                    "chunk_type": "keywords"
                })
                ids.append(f"{s.id}_keywords")

                # 3. Examples Chunk
                ex_list = s.examples if isinstance(s.examples, list) else []
                ex_str = ", ".join(ex_list)
                ex_doc = (
                    f"Sector: {s.name}\n"
                    f"Representative Companies & Businesses: {ex_str}"
                )
                documents.append(ex_doc)
                metadatas.append({
                    "sector_id": s.id,
                    "sector_name": s.name,
                    "chunk_type": "examples"
                })
                ids.append(f"{s.id}_examples")

            if documents:
                embeddings = self.embedding_provider.embed_documents(documents)
                self.vector_store.add_documents(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
                gc.collect()

            logger.info(f"Successfully indexed {len(documents)} sector chunks across {len(sectors)} sectors.")
            return len(documents)
        finally:
            if close_db:
                db.close()

    def index_single_sector(self, sector: Sector) -> None:
        """Deletes and re-indexes chunks for a single sector."""
        self.vector_store.delete_by_sector(sector.id)
        if not sector.active:
            logger.info(f"Sector {sector.id} is inactive, removed from vector index.")
            return

        documents = []
        metadatas = []
        ids = []

        # Description
        documents.append(f"Sector: {sector.name}\nDescription: {sector.description}\nDisambiguation: {sector.notes or ''}")
        metadatas.append({"sector_id": sector.id, "sector_name": sector.name, "chunk_type": "description"})
        ids.append(f"{sector.id}_description")

        # Keywords
        kw_list = sector.keywords if isinstance(sector.keywords, list) else []
        documents.append(f"Sector: {sector.name}\nCore Industry Keywords: {', '.join(kw_list)}")
        metadatas.append({"sector_id": sector.id, "sector_name": sector.name, "chunk_type": "keywords"})
        ids.append(f"{sector.id}_keywords")

        # Examples
        ex_list = sector.examples if isinstance(sector.examples, list) else []
        documents.append(f"Sector: {sector.name}\nRepresentative Companies & Businesses: {', '.join(ex_list)}")
        metadatas.append({"sector_id": sector.id, "sector_name": sector.name, "chunk_type": "examples"})
        ids.append(f"{sector.id}_examples")

        embeddings = self.embedding_provider.embed_documents(documents)
        self.vector_store.add_documents(documents, metadatas, ids, embeddings)
        logger.info(f"Indexed 3 chunks for sector {sector.id}.")

    def add_example_to_sector(self, sector_id: str, new_example: str, db: Optional[Session] = None) -> bool:
        """Adds a confirmed reviewer example to the sector knowledge base and updates vector store."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            sector = db.query(Sector).filter(Sector.id == sector_id).first()
            if not sector:
                return False
            examples = list(sector.examples or [])
            if new_example not in examples:
                examples.append(new_example)
                sector.examples = examples
                db.commit()
                self.index_single_sector(sector)
                logger.info(f"Appended example '{new_example}' to sector {sector_id} and refreshed index.")
            return True
        finally:
            if close_db:
                db.close()
