from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from app.db.models import Company, Contact
from app.extraction.schemas import ExtractedLeadData
from app.extraction.normalizer import normalize_company_name, normalize_domain_from_url
from app.ingestion.free_mail import is_free_mail_domain, extract_domain
from app.core.logging import logger


class DuplicateMatchResult:
    def __init__(
        self,
        match_type: str,  # 'exact_contact', 'domain_company', 'fuzzy_company', 'potential_fuzzy', 'none'
        matched_company_id: Optional[int] = None,
        matched_contact_id: Optional[int] = None,
        similarity_score: float = 100.0,
        rule_applied: str = "none",
        details: Optional[Dict[str, Any]] = None
    ):
        self.match_type = match_type
        self.matched_company_id = matched_company_id
        self.matched_contact_id = matched_contact_id
        self.similarity_score = round(similarity_score, 2)
        self.rule_applied = rule_applied
        self.details = details or {}


def detect_duplicates(lead: ExtractedLeadData, db: Session) -> DuplicateMatchResult:
    """
    Applies the 3 mandatory duplicate detection rules:
    Rule 1: Exact normalized email match
    Rule 2: Same company business domain (excluding free-mail)
    Rule 3: Fuzzy company matching (RapidFuzz token_set_ratio)
            >= 90 with same or missing domain -> Auto-merge
            80-90 with different domains -> Flag as possible duplicate
    """
    normalized_email = (lead.email or "").strip().lower()

    # RULE 1: Exact Email Match
    if normalized_email:
        existing_contact = db.query(Contact).filter(Contact.email == normalized_email).first()
        if existing_contact:
            logger.info(f"Rule 1 triggered: Contact with email {normalized_email} already exists (ID: {existing_contact.id}).")
            return DuplicateMatchResult(
                match_type="exact_contact",
                matched_company_id=existing_contact.company_id,
                matched_contact_id=existing_contact.id,
                similarity_score=100.0,
                rule_applied="RULE_1_EXACT_EMAIL",
                details={"contact_id": existing_contact.id, "email": normalized_email}
            )

    # Resolve company domain
    email_domain = extract_domain(normalized_email)
    web_domain = normalize_domain_from_url(lead.website)
    candidate_domain = web_domain or email_domain
    if is_free_mail_domain(candidate_domain):
        candidate_domain = None

    # RULE 2: Same Company Domain Match
    if candidate_domain:
        existing_domain_company = db.query(Company).filter(
            Company.domain == candidate_domain,
            Company.status != "merged"
        ).first()
        if existing_domain_company:
            logger.info(f"Rule 2 triggered: Company with domain {candidate_domain} found (ID: {existing_domain_company.id}).")
            return DuplicateMatchResult(
                match_type="domain_company",
                matched_company_id=existing_domain_company.id,
                similarity_score=100.0,
                rule_applied="RULE_2_SAME_DOMAIN",
                details={"domain": candidate_domain, "company_id": existing_domain_company.id}
            )

    # RULE 3: Fuzzy Company Matching via RapidFuzz
    target_norm_name = normalize_company_name(lead.company_name)
    if target_norm_name and len(target_norm_name) >= 3:
        # Load all active companies
        companies = db.query(Company).filter(
            Company.normalized_name.isnot(None),
            Company.status != "merged"
        ).all()

        best_score = 0.0
        best_company = None
        for comp in companies:
            if not comp.normalized_name:
                continue
            score = fuzz.token_set_ratio(target_norm_name, comp.normalized_name)
            if score > best_score:
                best_score = score
                best_company = comp

        if best_company:
            same_or_missing_domain = (
                not candidate_domain or
                not best_company.domain or
                candidate_domain == best_company.domain
            )

            # Similarity >= 90 with same or missing domain -> Auto merge
            if best_score >= 90.0 and same_or_missing_domain:
                logger.info(f"Rule 3 triggered (Auto-merge): Fuzzy match {best_score:.1f}% between '{target_norm_name}' and '{best_company.normalized_name}'.")
                return DuplicateMatchResult(
                    match_type="fuzzy_company",
                    matched_company_id=best_company.id,
                    similarity_score=best_score,
                    rule_applied="RULE_3_FUZZY_NAME_HIGH",
                    details={
                        "target_name": lead.company_name,
                        "matched_name": best_company.name,
                        "score": best_score
                    }
                )

            # Similarity between 80 and 90 (or >=90 with differing domains) -> Flag possible duplicate
            if 80.0 <= best_score < 90.0 or (best_score >= 90.0 and not same_or_missing_domain):
                logger.info(f"Rule 3 flag: Potential duplicate flagged ({best_score:.1f}%) between '{target_norm_name}' and '{best_company.normalized_name}'.")
                return DuplicateMatchResult(
                    match_type="potential_fuzzy",
                    matched_company_id=best_company.id,
                    similarity_score=best_score,
                    rule_applied="RULE_3_POTENTIAL_DUPLICATE_FLAG",
                    details={
                        "target_name": lead.company_name,
                        "matched_name": best_company.name,
                        "score": best_score,
                        "target_domain": candidate_domain,
                        "matched_domain": best_company.domain
                    }
                )

    return DuplicateMatchResult(match_type="none")
