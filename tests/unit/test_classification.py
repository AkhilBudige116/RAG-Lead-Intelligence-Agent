import pytest
from app.classification.confidence import evaluate_decision_gate
from app.classification.cache import generate_cache_key, get_cached_classification, set_cached_classification
from app.classification.engine import SectorClassifier
from app.extraction.schemas import ExtractedLeadData
from app.rag.retriever import SectorRetriever


def test_confidence_calculation_and_decision_gate():
    active_sectors = {"IT & Software", "Healthcare & Pharmaceuticals", "Finance & Insurance"}

    # High confidence classification: 0.6 * 0.9 + 0.4 * 0.9 = 0.90 -> classified
    res_high = evaluate_decision_gate(
        llm_confidence=0.90,
        top_retrieval_similarity=0.90,
        sector_name="IT & Software",
        has_company_name=True,
        has_business_summary=True,
        active_sector_names=active_sectors
    )
    assert res_high.final_confidence == 0.90
    assert res_high.status == "classified"

    # Mid confidence review: 0.6 * 0.7 + 0.4 * 0.5 = 0.62 -> needs_review
    res_mid = evaluate_decision_gate(
        llm_confidence=0.70,
        top_retrieval_similarity=0.50,
        sector_name="IT & Software",
        has_company_name=True,
        has_business_summary=True,
        active_sector_names=active_sectors
    )
    assert res_mid.final_confidence == 0.62
    assert res_mid.status == "needs_review"

    # Missing company name -> needs_review
    res_missing = evaluate_decision_gate(
        llm_confidence=0.95,
        top_retrieval_similarity=0.95,
        sector_name="IT & Software",
        has_company_name=False,
        has_business_summary=True,
        active_sector_names=active_sectors
    )
    assert res_missing.status == "needs_review"


def test_classification_caching():
    key = generate_cache_key("Cloud hosting platform", "v1_13")
    data = {"classification": {"sector": "IT & Software", "confidence": 0.9, "reason": "Test", "evidence": []}}
    set_cached_classification(key, data)
    cached = get_cached_classification(key)
    assert cached is not None
    assert cached["classification"]["sector"] == "IT & Software"
