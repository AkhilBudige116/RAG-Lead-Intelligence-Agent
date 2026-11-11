from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from app.db.models import Company, Contact, Email, Classification, DuplicateLog, Sector
from app.extraction.schemas import ExtractedLeadData, ClassificationResult
from app.ingestion.parser import ParsedEmailData
from app.classification.confidence import DecisionGateResult
from app.rag.retriever import RetrievalTrace
from app.dedup.detector import detect_duplicates, DuplicateMatchResult
from app.extraction.normalizer import normalize_company_name, normalize_domain_from_url
from app.ingestion.free_mail import is_free_mail_domain, extract_domain
from app.core.logging import logger


class ConsolidationResult:
    def __init__(
        self,
        company: Company,
        contact: Contact,
        email_record: Email,
        is_duplicate: bool,
        duplicate_rule: Optional[str] = None,
        potential_duplicate_of: Optional[int] = None
    ):
        self.company = company
        self.contact = contact
        self.email_record = email_record
        self.is_duplicate = is_duplicate
        self.duplicate_rule = duplicate_rule
        self.potential_duplicate_of = potential_duplicate_of


def consolidate_lead(
    lead: ExtractedLeadData,
    raw_email: ParsedEmailData,
    classification: ClassificationResult,
    gate: DecisionGateResult,
    trace: RetrievalTrace,
    matched_sector: Optional[Sector],
    batch_id: Optional[str],
    db: Session
) -> ConsolidationResult:
    """
    Consolidates incoming lead records into the relational database according to business rules:
    - Maintains one company record per business entity.
    - Multiple contacts per company.
    - Multiple emails per contact.
    - Preserves highest-confidence classification.
    - Flags conflicting sector assignments.
    - Records audit history in duplicate_log.
    """
    dup_match = detect_duplicates(lead, db)
    candidate_domain = normalize_domain_from_url(lead.website) or extract_domain(lead.email)
    if is_free_mail_domain(candidate_domain):
        candidate_domain = None

    normalized_name = normalize_company_name(lead.company_name)

    # 1. Existing Company Resolution
    target_company = None
    target_contact = None
    is_duplicate = False
    duplicate_rule = None
    potential_dup_id = None

    if dup_match.match_type in ("exact_contact", "domain_company", "fuzzy_company"):
        is_duplicate = True
        duplicate_rule = dup_match.rule_applied
        target_company = db.query(Company).filter(Company.id == dup_match.matched_company_id).first()

        if dup_match.match_type == "exact_contact":
            target_contact = db.query(Contact).filter(Contact.id == dup_match.matched_contact_id).first()
            if target_contact:
                target_contact.email_count += 1
                if lead.phones and not target_contact.phone:
                    target_contact.phone = lead.phones[0]
                if lead.job_title and not target_contact.title:
                    target_contact.title = lead.job_title

    elif dup_match.match_type == "potential_fuzzy":
        potential_dup_id = dup_match.matched_company_id

    # 2. If no existing company to merge into, create new Company
    if not target_company:
        target_company = Company(
            name=lead.company_name,
            normalized_name=normalized_name,
            domain=candidate_domain,
            website=lead.website,
            sector_id=matched_sector.id if matched_sector else None,
            confidence=gate.final_confidence,
            classification_reason=classification.reason,
            status=gate.status
        )
        db.add(target_company)
        db.flush()  # Generates target_company.id
    else:
        # Existing company: Preserve highest confidence & detect conflicts
        old_conf = target_company.confidence or 0.0
        new_conf = gate.final_confidence
        new_sector_id = matched_sector.id if matched_sector else None

        if new_conf > old_conf:
            # Check for conflicting sector
            if target_company.sector_id and new_sector_id and target_company.sector_id != new_sector_id:
                conflict_note = f"[Sector Conflict: Was {target_company.sector_id}, updated to {new_sector_id} with higher conf {new_conf:.2f}] "
                target_company.classification_reason = conflict_note + (classification.reason or "")
            else:
                target_company.classification_reason = classification.reason

            target_company.sector_id = new_sector_id
            target_company.confidence = new_conf
            target_company.status = gate.status

        # Enrich missing company fields
        if not target_company.website and lead.website:
            target_company.website = lead.website
        if not target_company.domain and candidate_domain:
            target_company.domain = candidate_domain
        if not target_company.name and lead.company_name:
            target_company.name = lead.company_name
            target_company.normalized_name = normalized_name

    # 3. Contact Resolution
    if not target_contact:
        target_contact = db.query(Contact).filter(Contact.email == lead.email).first()
        if not target_contact:
            target_contact = Contact(
                company_id=target_company.id,
                name=lead.contact_name,
                title=lead.job_title,
                email=lead.email,
                phone=lead.phones[0] if lead.phones else None,
                email_count=1
            )
            db.add(target_contact)
            db.flush()
        else:
            target_contact.company_id = target_company.id
            target_contact.email_count += 1

    # 4. Create Email Record (checking raw_hash uniqueness)
    existing_email = db.query(Email).filter(Email.raw_hash == raw_email.raw_hash).first()
    if existing_email:
        email_record = existing_email
    else:
        email_record = Email(
            batch_id=batch_id,
            contact_id=target_contact.id,
            company_id=target_company.id,
            sender_name=raw_email.sender_name,
            sender_email=raw_email.sender_email,
            subject=raw_email.subject,
            body=raw_email.body,
            signature=raw_email.signature,
            received_at=raw_email.received_at,
            source_file=raw_email.source_file,
            raw_hash=raw_email.raw_hash,
            evidence_sources=lead.evidence_sources
        )
        db.add(email_record)

    # 5. Create Classification Trace Record
    classification_entry = Classification(
        company_id=target_company.id,
        sector_id=matched_sector.id if matched_sector else None,
        confidence=gate.final_confidence,
        llm_confidence=gate.llm_confidence,
        top_retrieval_similarity=gate.top_retrieval_similarity,
        reason=classification.reason,
        evidence=classification.evidence,
        retrieved_sector_ids=trace.retrieved_sector_ids,
        model_version=trace.embedding_model_version,
        reviewed_by=None
    )
    db.add(classification_entry)

    # 6. Record Duplicate Log if potential or auto-merged
    if potential_dup_id:
        dup_log = DuplicateLog(
            kept_company_id=potential_dup_id,
            merged_company_id=target_company.id,
            rule="RULE_3_POTENTIAL_DUPLICATE_FLAG",
            details=dup_match.details,
            active=False  # Requires reviewer confirmation
        )
        db.add(dup_log)
    elif is_duplicate and dup_match.match_type == "fuzzy_company":
        dup_log = DuplicateLog(
            kept_company_id=target_company.id,
            merged_company_id=target_company.id,
            rule=duplicate_rule or "FUZZY_AUTO_MERGE",
            details=dup_match.details,
            active=True
        )
        db.add(dup_log)

    db.commit()
    db.refresh(target_company)
    db.refresh(target_contact)

    return ConsolidationResult(
        company=target_company,
        contact=target_contact,
        email_record=email_record,
        is_duplicate=is_duplicate,
        duplicate_rule=duplicate_rule,
        potential_duplicate_of=potential_dup_id
    )


def manual_merge_companies(kept_company_id: int, merged_company_id: int, db: Session) -> Optional[DuplicateLog]:
    """
    Manually merges merged_company_id into kept_company_id with full audit trail.
    Transfers contacts and emails, marks merged company as merged.
    """
    if kept_company_id == merged_company_id:
        return None

    kept = db.query(Company).filter(Company.id == kept_company_id).first()
    merged = db.query(Company).filter(Company.id == merged_company_id).first()
    if not kept or not merged:
        return None

    # Transfer contacts
    for contact in merged.contacts:
        contact.company_id = kept.id

    # Transfer emails
    for email in merged.emails:
        email.company_id = kept.id

    # Preserve higher confidence
    if (merged.confidence or 0.0) > (kept.confidence or 0.0):
        kept.sector_id = merged.sector_id
        kept.confidence = merged.confidence
        kept.classification_reason = f"[Merged from {merged.name}] " + (merged.classification_reason or "")

    # Mark merged status
    merged.status = "merged"
    merged.merged_into_id = kept.id

    log_entry = DuplicateLog(
        kept_company_id=kept.id,
        merged_company_id=merged.id,
        rule="MANUAL_CONFIRMED_MERGE",
        details={
            "kept_company_name": kept.name,
            "merged_company_name": merged.name,
            "contacts_transferred": len(merged.contacts)
        },
        active=True
    )
    db.add(log_entry)
    db.commit()
    db.refresh(kept)
    logger.info(f"Successfully merged company {merged.id} ({merged.name}) into {kept.id} ({kept.name}).")
    return log_entry


def undo_merge(duplicate_log_id: int, db: Session) -> bool:
    """
    Reverts a previous merge operation. Restores original company status and unlinks records.
    """
    log_entry = db.query(DuplicateLog).filter(
        DuplicateLog.id == duplicate_log_id,
        DuplicateLog.active == True
    ).first()
    if not log_entry:
        return False

    merged_comp = db.query(Company).filter(Company.id == log_entry.merged_company_id).first()
    if not merged_comp:
        return False

    # Restore merged company status
    merged_comp.status = "needs_review"
    merged_comp.merged_into_id = None

    # Re-link contacts whose emails or origin belonged to this merged company
    contacts = db.query(Contact).filter(Contact.company_id == log_entry.kept_company_id).all()
    # (Optionally restore contacts if their email domains match merged company)
    for c in contacts:
        if merged_comp.domain and extract_domain(c.email) == merged_comp.domain:
            c.company_id = merged_comp.id

    emails = db.query(Email).filter(Email.company_id == log_entry.kept_company_id).all()
    for e in emails:
        if merged_comp.domain and extract_domain(e.sender_email or "") == merged_comp.domain:
            e.company_id = merged_comp.id

    log_entry.active = False
    db.commit()
    logger.info(f"Undid merge for DuplicateLog {duplicate_log_id}: restored company {merged_comp.id}.")
    return True
