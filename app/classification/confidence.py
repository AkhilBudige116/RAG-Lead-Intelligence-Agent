from typing import Tuple, Optional
from app.core.config import settings
from app.core.logging import logger


class DecisionGateResult:
    def __init__(
        self,
        final_confidence: float,
        llm_confidence: float,
        top_retrieval_similarity: float,
        status: str,  # 'classified', 'needs_review'
        decision_reason: str
    ):
        self.final_confidence = round(final_confidence, 4)
        self.llm_confidence = round(llm_confidence, 4)
        self.top_retrieval_similarity = round(top_retrieval_similarity, 4)
        self.status = status
        self.decision_reason = decision_reason

    def to_dict(self):
        return {
            "final_confidence": self.final_confidence,
            "llm_confidence": self.llm_confidence,
            "top_retrieval_similarity": self.top_retrieval_similarity,
            "status": self.status,
            "decision_reason": self.decision_reason
        }


def evaluate_decision_gate(
    llm_confidence: float,
    top_retrieval_similarity: float,
    sector_name: str,
    has_company_name: bool,
    has_business_summary: bool,
    active_sector_names: set
) -> DecisionGateResult:
    """
    Computes final confidence score and applies company assessment decision rules:
    final_confidence = (0.6 * llm_confidence) + (0.4 * top_retrieval_similarity)
    """
    final_conf = (0.6 * float(llm_confidence)) + (0.4 * float(top_retrieval_similarity))

    # Condition 1: Missing company or business evidence
    if not has_company_name or not has_business_summary:
        return DecisionGateResult(
            final_confidence=final_conf,
            llm_confidence=llm_confidence,
            top_retrieval_similarity=top_retrieval_similarity,
            status="needs_review",
            decision_reason="Flagged for review due to missing company name or insufficient business evidence."
        )

    # Condition 2: LLM explicit Needs Review or Other / Unknown
    if sector_name in ("Needs Review", "needs_review", "Other / Unknown", "Unknown"):
        return DecisionGateResult(
            final_confidence=final_conf,
            llm_confidence=llm_confidence,
            top_retrieval_similarity=top_retrieval_similarity,
            status="needs_review",
            decision_reason="Model returned Needs Review or unclassified sector."
        )

    # Condition 3: Invalid sector (not in active list)
    if sector_name not in active_sector_names:
        return DecisionGateResult(
            final_confidence=final_conf,
            llm_confidence=llm_confidence,
            top_retrieval_similarity=top_retrieval_similarity,
            status="needs_review",
            decision_reason=f"Sector '{sector_name}' is not in active approved sectors list."
        )

    # Condition 4: Insufficient retrieval evidence
    if top_retrieval_similarity < 0.20:
        return DecisionGateResult(
            final_confidence=final_conf,
            llm_confidence=llm_confidence,
            top_retrieval_similarity=top_retrieval_similarity,
            status="needs_review",
            decision_reason="Insufficient retrieval similarity with sector knowledge base."
        )

    # Threshold Gate
    threshold = settings.CONFIDENCE_THRESHOLD
    min_review = settings.REVIEW_THRESHOLD_MIN

    if final_conf >= threshold:
        status = "classified"
        reason = f"Confidence {final_conf:.2f} satisfies threshold >= {threshold:.2f}."
    elif final_conf >= min_review:
        status = "needs_review"
        reason = f"Confidence {final_conf:.2f} is in review range [{min_review:.2f}, {threshold:.2f})."
    else:
        status = "needs_review"
        reason = f"Low confidence {final_conf:.2f} < {min_review:.2f}."

    return DecisionGateResult(
        final_confidence=final_conf,
        llm_confidence=llm_confidence,
        top_retrieval_similarity=top_retrieval_similarity,
        status=status,
        decision_reason=reason
    )
