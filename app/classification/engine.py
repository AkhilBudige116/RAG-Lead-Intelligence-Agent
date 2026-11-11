import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.db.models import Sector
from app.db.session import SessionLocal
from app.extraction.schemas import ExtractedLeadData, ClassificationResult
from app.rag.retriever import RetrievalTrace
from app.classification.confidence import evaluate_decision_gate, DecisionGateResult
from app.classification.cache import (
    generate_cache_key,
    get_cached_classification,
    set_cached_classification
)
from app.core.config import settings
from app.core.logging import logger
from app.core.security import detect_and_neutralize_prompt_injection

try:
    import anthropic
except ImportError:
    anthropic = None


CLASSIFICATION_SYSTEM_PROMPT = """You classify business leads into industry sectors.
Use ONLY the provided sector definitions and actual business evidence.
If evidence is insufficient or ambiguous, return Needs Review.
Do not guess based on company name alone.
Return valid JSON containing:
sector,
confidence,
reason,
evidence."""


class SectorClassifier:
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._client = None
        if settings.LLM_API_KEY and anthropic is not None and settings.LLM_PROVIDER in ("anthropic", "auto"):
            try:
                self._client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
                logger.info("Initialized Anthropic Claude client for lead classification.")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}. Falling back to deterministic mode.")

    def classify_lead(
        self,
        lead: ExtractedLeadData,
        retrieval_trace: RetrievalTrace,
        db: Optional[Session] = None
    ) -> Tuple[ClassificationResult, DecisionGateResult, Optional[Sector]]:
        """
        Classifies lead into active industry sectors using RAG retrieval trace.
        Returns (ClassificationResult, DecisionGateResult, MatchedSectorModel).
        """
        active_sectors_map = self._get_active_sectors(db)
        active_names = {s.name for s in active_sectors_map.values()}

        # 1. Missing evidence check
        if not lead.business_summary and not lead.company_name:
            unclass = ClassificationResult(
                sector="Needs Review",
                confidence=0.0,
                reason="No company name or business summary was found in email.",
                evidence=[]
            )
            gate = evaluate_decision_gate(
                llm_confidence=0.0,
                top_retrieval_similarity=retrieval_trace.top_similarity,
                sector_name=unclass.sector,
                has_company_name=bool(lead.company_name),
                has_business_summary=bool(lead.business_summary),
                active_sector_names=active_names
            )
            return unclass, gate, None

        # 2. Check cache
        cache_key = generate_cache_key(
            lead_summary=lead.business_summary or lead.company_name or "",
            sector_version=f"v1_{len(active_names)}"
        )
        cached = get_cached_classification(cache_key)
        if cached:
            cl_res = ClassificationResult(**cached["classification"])
            matched_sector = active_sectors_map.get(cl_res.sector.lower())
            gate = evaluate_decision_gate(
                llm_confidence=cl_res.confidence,
                top_retrieval_similarity=retrieval_trace.top_similarity,
                sector_name=cl_res.sector,
                has_company_name=bool(lead.company_name),
                has_business_summary=bool(lead.business_summary),
                active_sector_names=active_names
            )
            return cl_res, gate, matched_sector

        # 3. Perform classification (Claude or Deterministic Mock)
        if self._client and settings.LLM_API_KEY:
            cl_res = self._call_claude_with_retry(lead, retrieval_trace, active_names)
        else:
            cl_res = self._mock_deterministic_classify(lead, retrieval_trace, active_sectors_map)

        # 4. Resolve Matched Sector Database Entity
        matched_sector = None
        for sec in active_sectors_map.values():
            if sec.name.lower() == cl_res.sector.lower() or sec.id.lower() == cl_res.sector.lower():
                matched_sector = sec
                # Standardize to official sector name
                cl_res.sector = sec.name
                break

        # 5. Evaluate Decision Gate
        gate = evaluate_decision_gate(
            llm_confidence=cl_res.confidence,
            top_retrieval_similarity=retrieval_trace.top_similarity,
            sector_name=cl_res.sector,
            has_company_name=bool(lead.company_name),
            has_business_summary=bool(lead.business_summary),
            active_sector_names=active_names
        )

        # 6. Cache result
        set_cached_classification(cache_key, {
            "classification": cl_res.model_dump(),
            "gate": gate.to_dict()
        })

        return cl_res, gate, matched_sector

    def _call_claude_with_retry(
        self,
        lead: ExtractedLeadData,
        retrieval_trace: RetrievalTrace,
        active_names: Set[str]
    ) -> ClassificationResult:
        """Calls Anthropic Claude API with automatic retry on format failure."""
        prompt = self._build_prompt(lead, retrieval_trace, list(active_names))

        for attempt in range(2):
            try:
                msg = self._client.messages.create(
                    model=settings.LLM_MODEL,
                    max_tokens=600,
                    temperature=settings.LLM_TEMPERATURE,
                    system=CLASSIFICATION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw_text = msg.content[0].text.strip()
                parsed = self._parse_json_response(raw_text)
                if parsed:
                    validated = ClassificationResult(**parsed)
                    # Validate active sector
                    if validated.sector in active_names or validated.sector == "Needs Review":
                        return validated
                    else:
                        logger.warning(f"Attempt {attempt+1}: LLM returned inactive sector '{validated.sector}'.")
            except Exception as e:
                logger.warning(f"Claude classification attempt {attempt+1} failed: {e}")

        # If retry fails, return Needs Review
        return ClassificationResult(
            sector="Needs Review",
            confidence=0.40,
            reason="Classification failed validation after retry.",
            evidence=[]
        )

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        clean = text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        try:
            return json.loads(clean)
        except Exception:
            # Try finding json block inside text
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    def _build_prompt(self, lead: ExtractedLeadData, retrieval_trace: RetrievalTrace, active_names: List[str]) -> str:
        safe_summary = detect_and_neutralize_prompt_injection(lead.business_summary or "")
        safe_company = detect_and_neutralize_prompt_injection(lead.company_name or "")
        allowed_sectors = ", ".join(sorted(active_names))

        return f"""CLASSIFY THE BUSINESS LEAD:

LEAD DETAILS:
Company Name: {safe_company}
Website: {lead.website or 'N/A'}
Job Title: {lead.job_title or 'N/A'}
Business Summary: {safe_summary}

ALLOWED ACTIVE SECTORS:
{allowed_sectors}

RETRIEVED SECTOR KNOWLEDGE BASE EVIDENCE:
{retrieval_trace.sector_definitions_text}

INSTRUCTIONS:
1. Compare the business summary and services against the retrieved sector definitions.
2. If business evidence is ambiguous or missing, set sector to "Needs Review".
3. Return ONLY a valid JSON object matching this schema:
{{
  "sector": "<Exact Sector Name from Allowed Sectors or Needs Review>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<Detailed factual explanation for why this sector matches the evidence>",
  "evidence": ["<key phrase 1>", "<key phrase 2>"]
}}"""

    def _mock_deterministic_classify(
        self,
        lead: ExtractedLeadData,
        retrieval_trace: RetrievalTrace,
        active_sectors_map: Dict[str, Sector]
    ) -> ClassificationResult:
        """
        High-precision deterministic classification engine for mock / offline testing.
        Uses exact keyword matching and RAG similarity to select sector and quote evidence.
        """
        text_corpus = f"{lead.business_summary or ''} {lead.company_name or ''} {lead.job_title or ''}".lower()

        best_sector = None
        best_score = 0.0
        matching_keywords = []

        # Evaluate against active sectors
        for sec_id, sec in active_sectors_map.items():
            score = 0.0
            found_kw = []
            keywords = sec.keywords if isinstance(sec.keywords, list) else []
            for kw in keywords:
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, text_corpus):
                    score += 1.5
                    found_kw.append(kw)

            examples = sec.examples if isinstance(sec.examples, list) else []
            for ex in examples:
                if ex.lower() in text_corpus:
                    score += 2.0
                    found_kw.append(ex)

            # Add RAG retrieval similarity boost
            if sec.id in retrieval_trace.retrieved_sector_ids:
                score += (retrieval_trace.top_similarity * 2.0)

            if score > best_score:
                best_score = score
                best_sector = sec
                matching_keywords = found_kw

        if best_sector and best_score >= 1.5:
            # Scale confidence between 0.78 and 0.96 based on match strength
            conf = min(0.96, 0.75 + (min(best_score, 6.0) / 30.0))
            reason = f"Company matches {best_sector.name} based on business offerings: {', '.join(matching_keywords[:3])}."
            return ClassificationResult(
                sector=best_sector.name,
                confidence=round(conf, 2),
                reason=reason,
                evidence=matching_keywords[:4]
            )

        # If retrieved sector exists with high similarity
        if retrieval_trace.retrieved_chunks and retrieval_trace.top_similarity > 0.82:
            top_chunk = retrieval_trace.retrieved_chunks[0]
            sec_id = top_chunk["metadata"].get("sector_id")
            if sec_id and sec_id in active_sectors_map:
                sec = active_sectors_map[sec_id]
                return ClassificationResult(
                    sector=sec.name,
                    confidence=0.80,
                    reason=f"Retrieved high similarity ({retrieval_trace.top_similarity:.2f}) with sector definition.",
                    evidence=[lead.business_summary[:80]] if lead.business_summary else []
                )

        # Ambiguous or weak match
        return ClassificationResult(
            sector="Needs Review",
            confidence=0.55,
            reason="Ambiguous or insufficient business evidence to confidently determine industry sector.",
            evidence=[]
        )

    def _get_active_sectors(self, db: Optional[Session] = None) -> Dict[str, Sector]:
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            sectors = db.query(Sector).filter(Sector.active == True).all()
            return {s.name.lower(): s for s in sectors}
        finally:
            if close_db:
                db.close()
