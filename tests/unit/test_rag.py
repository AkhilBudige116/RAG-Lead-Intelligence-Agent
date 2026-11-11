import pytest
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store
from app.rag.retriever import SectorRetriever
from app.extraction.schemas import ExtractedLeadData


def test_embedding_generation():
    provider = get_embedding_provider()
    doc_embs = provider.embed_documents(["Software development and cloud services", "Pharmaceutical clinical trials"])
    assert len(doc_embs) == 2
    assert len(doc_embs[0]) == len(doc_embs[1])

    q_emb = provider.embed_query("Fintech banking and payments")
    assert len(q_emb) == len(doc_embs[0])


def test_vector_store_retrieval():
    retriever = SectorRetriever()
    lead = ExtractedLeadData(
        company_name="Moderna Therapeutics",
        email="info@modernatx.com",
        website="https://modernatx.com",
        business_summary="Developing mRNA therapeutics and vaccines for infectious diseases and oncology."
    )
    trace = retriever.retrieve(lead, top_k=5)

    assert len(trace.retrieved_chunks) > 0
    assert trace.top_similarity > 0.0
    assert "healthcare_pharma" in trace.retrieved_sector_ids
    assert len(trace.sector_definitions_text) > 0
