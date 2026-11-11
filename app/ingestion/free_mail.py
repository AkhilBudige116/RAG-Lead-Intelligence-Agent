from typing import Set

# Comprehensive set of consumer/free webmail domains
FREE_MAIL_DOMAINS: Set[str] = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.in",
    "yahoo.co.uk",
    "yahoo.fr",
    "yahoo.de",
    "hotmail.com",
    "hotmail.co.uk",
    "outlook.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "mail.com",
    "zoho.com",
    "protonmail.com",
    "proton.me",
    "tutanota.com",
    "yandex.com",
    "yandex.ru",
    "gmx.com",
    "gmx.de",
    "fastmail.com",
    "inbox.com",
    "rediffmail.com"
}


def is_free_mail_domain(domain_or_email: str) -> bool:
    """Check whether a domain or email belongs to a free consumer mail provider."""
    if not domain_or_email:
        return False
    domain = domain_or_email.lower().strip()
    if "@" in domain:
        domain = domain.split("@")[-1].strip()
    return domain in FREE_MAIL_DOMAINS


def extract_domain(email_address: str) -> str:
    """Extract domain part from an email address."""
    if not email_address or "@" not in email_address:
        return ""
    return email_address.split("@")[-1].strip().lower()
