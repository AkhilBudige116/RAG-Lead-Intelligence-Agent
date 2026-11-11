import datetime
from typing import List, Dict, Any, Optional
from app.extraction.schemas import ExtractedLeadData
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store
from app.core.logging import logger


class RetrievalTrace:
    def __init__(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        retrieved_sector_ids: List[str],
        top_similarity: float,
        sector_definitions_text: str,
        embedding_model_version: str,
        retrieval_timestamp: datetime.datetime
    ):
        self.query = query
        self.retrieved_chunks = retrieved_chunks
        self.retrieved_sector_ids = retrieved_sector_ids
        self.top_similarity = top_similarity
        self.sector_definitions_text = sector_definitions_text
        self.embedding_model_version = embedding_model_version
        self.retrieval_timestamp = retrieval_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "retrieved_sector_ids": self.retrieved_sector_ids,
            "top_similarity": self.top_similarity,
            "embedding_model_version": self.embedding_model_version,
            "retrieval_timestamp": self.retrieval_timestamp.isoformat(),
            "retrieved_chunks_count": len(self.retrieved_chunks)
        }


class SectorRetriever:
    def __init__(self, vector_store=None, embedding_provider=None):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def construct_query(self, lead: ExtractedLeadData, body_snippet: Optional[str] = None) -> str:
        """
        Constructs the retrieval query using:
        Business summary, Company name, Domain, Job title, Important email body phrases.
        """
        parts = []
        if lead.business_summary:
            parts.append(f"Business: {lead.business_summary}")
        if lead.company_name:
            parts.append(f"Company: {lead.company_name}")
        if lead.website:
            parts.append(f"Website: {lead.website}")
        if lead.job_title:
            parts.append(f"Role: {lead.job_title}")
        if body_snippet:
            clean_snippet = body_snippet[:300].strip()
            parts.append(f"Context: {clean_snippet}")

        query = " | ".join(parts).strip()
        return query or "General business enquiry"

    def retrieve(self, lead: ExtractedLeadData, body_snippet: Optional[str] = None, top_k: int = 5) -> RetrievalTrace:
        """
        Retrieves top K sector chunks, groups them by sector, and formats definitions for LLM.
        """
        query = self.construct_query(lead, body_snippet)
        query_embedding = self.embedding_provider.embed_query(query)
        chunks = self.vector_store.query_similar(query_embedding, top_k=top_k)

        top_similarity = chunks[0]["similarity"] if chunks else 0.0

        # Group chunks by sector
        grouped_by_sector: Dict[str, List[Dict[str, Any]]] = {}
        retrieved_sector_ids = []
        for ch in chunks:
            sec_id = ch["metadata"].get("sector_id")
            if sec_id:
                if sec_id not in retrieved_sector_ids:
                    retrieved_sector_ids.append(sec_id)
                grouped_by_sector.setdefault(sec_id, []).append(ch)

        # Build formatted sector definitions block for LLM prompt
        lines = []
        for sec_id, sector_chunks in grouped_by_sector.items():
            sec_name = sector_chunks[0]["metadata"].get("sector_name", sec_id)
            lines.append(f"### SECTOR: {sec_name} (ID: {sec_id})")
            for sc in sector_chunks:
                chunk_type = sc["metadata"].get("chunk_type", "definition")
                sim = sc["similarity"]
                lines.append(f"- [{chunk_type.upper()}] (Similarity: {sim:.3f}): {sc['document']}")
            lines.append("")

        definitions_text = "\n".join(lines).strip()
        if not definitions_text:
            definitions_text = "No sector definitions retrieved."

        return RetrievalTrace(
            query=query,
            retrieved_chunks=chunks,
            retrieved_sector_ids=retrieved_sector_ids,
            top_similarity=top_similarity,
            sector_definitions_text=definitions_text,
            embedding_model_version=self.embedding_provider.model_version,
            retrieval_timestamp=datetime.datetime.utcnow()
        )
