import pytest
from app.extraction.normalizer import (
    normalize_company_name,
    normalize_domain_from_url,
    standardize_phone_number,
    standardize_phone_list
)
from app.extraction.extractor import LeadExtractor
from app.ingestion.parser import ParsedEmailData
from app.extraction.schemas import ExtractedLeadData


def test_normalize_company_name():
    assert normalize_company_name("Acme Technologies Pvt Ltd") == "acme"
    assert normalize_company_name("Zenith Global Inc.") == "zenith global"
    assert normalize_company_name("Stripe LLC") == "stripe"
    assert normalize_company_name("Alphabet Corporation") == "alphabet"
    assert normalize_company_name(None) is None


def test_normalize_domain():
    assert normalize_domain_from_url("https://www.salesforce.com/products") == "salesforce.com"
    assert normalize_domain_from_url("http://stripe.com:8080/checkout") == "stripe.com"
    assert normalize_domain_from_url("gmail.com") is None  # Free-mail exclusion


def test_standardize_phone_number():
    phone_us = standardize_phone_number("415-555-2671", default_region="US")
    assert phone_us is not None
    assert "+1" in phone_us

    phone_in = standardize_phone_number("+91 98765 43210")
    assert "+91" in phone_in


def test_deterministic_lead_extractor():
    extractor = LeadExtractor()
    email = ParsedEmailData(
        sender_name="Alice Wang",
        sender_email="alice@biotechsolutions.com",
        subject="Clinical Diagnostics and Drug Discovery Collaboration",
        body="We are scaling up Phase II clinical trials for oncology therapeutics.",
        signature="Alice Wang\nDirector of Clinical Affairs\nBioTech Solutions Inc.\nPhone: +1 617-555-0199\nhttps://biotechsolutions.com",
        evidence_sources=["body", "signature"]
    )
    lead = extractor.extract(email)

    assert lead.contact_name == "Alice Wang"
    assert lead.email == "alice@biotechsolutions.com"
    assert lead.job_title == "Director of Clinical Affairs"
    assert "biotechsolutions.com" in (lead.website or "")
    assert len(lead.phones) >= 1
    assert "signature" in lead.evidence_sources


def test_free_mail_sender_protection():
    extractor = LeadExtractor()
    email = ParsedEmailData(
        sender_name="Random User",
        sender_email="randomuser@gmail.com",
        subject="Question",
        body="Just a quick question regarding pricing.",
        signature="Thanks,\nRandom"
    )
    lead = extractor.extract(email)
    # Never use gmail as company name
    assert lead.company_name is None
    assert lead.website is None
