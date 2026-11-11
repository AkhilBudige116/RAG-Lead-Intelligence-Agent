import io
import pytest
from app.ingestion.parser import (
    parse_file,
    parse_json_content,
    separate_body_and_signature,
    remove_quoted_replies
)
from app.ingestion.free_mail import is_free_mail_domain, extract_domain
from app.ingestion.validation import validate_file_upload, compute_sha256


def test_free_mail_domains():
    assert is_free_mail_domain("user@gmail.com") is True
    assert is_free_mail_domain("contact@yahoo.com") is True
    assert is_free_mail_domain("info@outlook.com") is True
    assert is_free_mail_domain("corp@acmecorp.com") is False
    assert is_free_mail_domain("sales@snowflake.com") is False
    assert extract_domain("alex@stripe.com") == "stripe.com"


def test_signature_separation():
    text = (
        "Hello,\nWe would like to explore your enterprise cloud integration platform.\n"
        "Let us know your availability for a call.\n\n"
        "Best regards,\nJohn Doe\nVP Engineering\nAcme Systems"
    )
    body, sig = separate_body_and_signature(text)
    assert "We would like to explore" in body
    assert sig is not None
    assert "Best regards" in sig
    assert "Acme Systems" in sig


def test_remove_quoted_replies():
    text = (
        "Here is the pricing proposal.\n\n"
        "> On Mon, Jan 10, 2026 at 10:00 AM user@domain.com wrote:\n"
        "> Can you send pricing?"
    )
    cleaned, _ = remove_quoted_replies(text)
    assert "Here is the pricing proposal." in cleaned
    assert "Can you send pricing" not in cleaned


def test_json_email_parsing():
    json_data = [
        {
            "sender_name": "Priya Sharma",
            "sender_email": "priya@zenith.ai",
            "subject": "AI Pipeline Development",
            "body": "We develop state-of-the-art computer vision and NLP models.",
            "signature": "Priya Sharma\nCTO, Zenith AI"
        }
    ]
    parsed = parse_json_content(json_data, "test.json")
    assert len(parsed) == 1
    assert parsed[0].sender_name == "Priya Sharma"
    assert parsed[0].sender_email == "priya@zenith.ai"
    assert "signature" in parsed[0].evidence_sources


def test_file_validation():
    valid, msg = validate_file_upload("test.eml", b"From: a@b.com\nSubject: Hi\n\nBody")
    assert valid is True

    invalid_ext, msg = validate_file_upload("test.exe", b"binary content")
    assert invalid_ext is False

    empty_file, msg = validate_file_upload("test.csv", b"")
    assert empty_file is False
