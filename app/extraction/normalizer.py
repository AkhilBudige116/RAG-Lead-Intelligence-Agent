import re
from typing import Optional, List
import phonenumbers
from urllib.parse import urlparse
from app.ingestion.free_mail import is_free_mail_domain

COMPANY_SUFFIXES = [
    r"\bpvt\.?\s*ltd\.?\b",
    r"\bprivate\s+limited\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bgmbh\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\benterprises\b",
    r"\bgroup\b",
    r"\bservices\b",
    r"\bsolutions\b",
    r"\btechnologies\b",
]

SUFFIX_REGEX = re.compile(r"|".join(COMPANY_SUFFIXES), re.IGNORECASE)


def normalize_company_name(name: Optional[str]) -> Optional[str]:
    """
    Normalizes company name for fuzzy duplicate detection and matching:
    removes punctuation, excess spaces, and legal suffixes (Pvt, Ltd, LLC, Inc).
    """
    if not name:
        return None

    cleaned = name.strip()
    # Remove legal suffixes
    cleaned = SUFFIX_REGEX.sub("", cleaned)
    # Remove non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()

    return cleaned if len(cleaned) > 1 else None


def normalize_domain_from_url(url_or_domain: Optional[str]) -> Optional[str]:
    """
    Extracts canonical domain (e.g. 'stripe.com' from 'https://www.stripe.com/pricing').
    Strips 'www.' and free-mail domains.
    """
    if not url_or_domain:
        return None

    candidate = url_or_domain.strip().lower()
    if not (candidate.startswith("http://") or candidate.startswith("https://")):
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
        netloc = parsed.netloc or parsed.path
        # Remove port if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        # Remove www.
        if netloc.startswith("www."):
            netloc = netloc[4:]
        netloc = netloc.strip().rstrip("/")
        if netloc and not is_free_mail_domain(netloc):
            return netloc
        return None
    except Exception:
        return None


def standardize_phone_number(raw_phone: str, default_region: str = "US") -> Optional[str]:
    """
    Standardizes a phone string into international format using google phonenumbers library.
    """
    if not raw_phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", raw_phone)
    if len(cleaned) < 7:
        return None

    # Try international parse or default region fallback
    try:
        # If starts with +, parse without region
        if cleaned.startswith("+"):
            parsed = phonenumbers.parse(cleaned, None)
        else:
            # Try region
            parsed = phonenumbers.parse(cleaned, default_region)
            if not phonenumbers.is_possible_number(parsed):
                # Try IN or GB fallback
                parsed = phonenumbers.parse(cleaned, "IN")

        if phonenumbers.is_possible_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        pass

    # Basic cleanup fallback
    return raw_phone.strip()


def standardize_phone_list(raw_phones: List[str]) -> List[str]:
    """Cleans and dedups a list of phone numbers."""
    results = []
    seen = set()
    for p in raw_phones:
        formatted = standardize_phone_number(p)
        if formatted and formatted not in seen:
            seen.add(formatted)
            results.append(formatted)
    return results
