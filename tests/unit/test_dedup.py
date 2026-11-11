import pytest
from app.db.models import Company, Contact
from app.dedup.detector import detect_duplicates
from app.extraction.schemas import ExtractedLeadData
from app.dedup.consolidator import manual_merge_companies, undo_merge


def test_dedup_rules(client):
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        # Create initial company & contact
        c1 = Company(
            name="Acme Solutions Pvt Ltd",
            normalized_name="acme",
            domain="acmesolutions.com",
            website="https://acmesolutions.com",
            status="classified",
            confidence=0.88
        )
        db.add(c1)
        db.flush()

        contact1 = Contact(
            company_id=c1.id,
            name="Bob Smith",
            email="bob@acmesolutions.com"
        )
        db.add(contact1)
        db.commit()

        # Rule 1: Exact Email
        lead_rule1 = ExtractedLeadData(
            company_name="Different Name",
            email="bob@acmesolutions.com",
            business_summary="Some service"
        )
        res1 = detect_duplicates(lead_rule1, db)
        assert res1.rule_applied == "RULE_1_EXACT_EMAIL"
        assert res1.matched_contact_id == contact1.id

        # Rule 2: Same Domain
        lead_rule2 = ExtractedLeadData(
            company_name="Another Dept",
            email="charlie@acmesolutions.com",
            business_summary="Some service"
        )
        res2 = detect_duplicates(lead_rule2, db)
        assert res2.rule_applied == "RULE_2_SAME_DOMAIN"
        assert res2.matched_company_id == c1.id

        # Rule 3: Fuzzy Name >= 90 with missing domain -> Auto-merge
        lead_rule3_merge = ExtractedLeadData(
            company_name="Acme Solutions Inc",
            email="sales@gmail.com",  # free-mail domain -> domain is None/missing
            business_summary="Some service"
        )
        res3_merge = detect_duplicates(lead_rule3_merge, db)
        assert res3_merge.rule_applied == "RULE_3_FUZZY_NAME_HIGH"
        assert res3_merge.matched_company_id == c1.id

        # Rule 3: Fuzzy Name >= 90 with DIFFERENT domain -> Flag possible duplicate
        lead_rule3_flag = ExtractedLeadData(
            company_name="Acme Solutions Inc",
            email="sales@differentdomain.com",
            business_summary="Some service"
        )
        res3_flag = detect_duplicates(lead_rule3_flag, db)
        assert res3_flag.rule_applied == "RULE_3_POTENTIAL_DUPLICATE_FLAG"
        assert res3_flag.matched_company_id == c1.id

    finally:
        db.close()
