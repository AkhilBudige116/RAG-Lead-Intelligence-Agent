import re
import json
from typing import List, Optional, Tuple, Dict, Any
import phonenumbers
from app.ingestion.parser import ParsedEmailData
from app.ingestion.free_mail import is_free_mail_domain, extract_domain
from app.extraction.schemas import ExtractedLeadData
from app.extraction.normalizer import (
    normalize_domain_from_url,
    standardize_phone_list,
    normalize_company_name
)
from app.core.config import settings
from app.core.logging import logger
from app.core.security import detect_and_neutralize_prompt_injection

URL_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s<>'\"()]*)?)",
    re.IGNORECASE
)

TITLE_KEYWORDS = [
    "director", "manager", "head", "lead", "officer", "vp", "vice president",
    "founder", "co-founder", "ceo", "cto", "cfo", "cmo", "coo", "cio",
    "engineer", "architect", "developer", "consultant", "analyst", "specialist",
    "coordinator", "administrator", "partner", "associate", "executive", "representative"
]

COMPANY_PREFIX_REGEX = re.compile(
    r"(?:company|organization|at|with)\s*:\s*(?P<comp>[A-Za-z0-9\s&.,'-]{2,50})",
    re.IGNORECASE
)


class LeadExtractor:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def extract(self, email: ParsedEmailData) -> ExtractedLeadData:
        """
        Extracts structured entity information from email headers, body, and signature.
        Combines deterministic regex/heuristic extraction with LLM when configured.
        """
        # Always run deterministic heuristic extraction first
        heur_data = self._extract_deterministic(email)

        # If LLM is available and enabled, we can enhance or use LLM extraction
        if settings.LLM_API_KEY and settings.LLM_PROVIDER in ("anthropic", "auto") and self.llm_client:
            try:
                llm_data = self._extract_llm(email, heur_data)
                if llm_data:
                    return llm_data
            except Exception as e:
                logger.warning(f"LLM extraction encountered error, falling back to deterministic extraction: {e}")

        return heur_data

    def _extract_deterministic(self, email: ParsedEmailData) -> ExtractedLeadData:
        """Rule-based, high-accuracy deterministic extraction."""
        evidence_sources = list(email.evidence_sources)
        sender_email = email.sender_email or ""
        domain = extract_domain(sender_email)
        is_free_mail = is_free_mail_domain(domain)

        # 1. Contact Name
        contact_name = email.sender_name
        if not contact_name and "@" in sender_email:
            local_part = sender_email.split("@")[0]
            # If name like 'john.doe', capitalize
            if "." in local_part or "_" in local_part:
                contact_name = " ".join(part.capitalize() for part in re.split(r"[._]", local_part) if not part.isdigit())

        # 2. Extract Phone Numbers from Signature & Body
        raw_text_for_search = (email.signature or "") + "\n" + (email.body or "")
        detected_phones: List[str] = []
        try:
            for match in phonenumbers.PhoneNumberMatcher(raw_text_for_search, "US"):
                detected_phones.append(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL))
        except Exception:
            pass

        # Fallback phone regex
        if not detected_phones:
            phone_matches = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text_for_search)
            detected_phones.extend(phone_matches)

        phones = standardize_phone_list(detected_phones)
        if phones and "signature" not in evidence_sources and email.signature:
            evidence_sources.append("signature")

        # 3. Extract Website
        website = None
        # Check signature first
        search_targets = [(email.signature, "signature"), (email.body, "body")]
        for text_block, src in search_targets:
            if not text_block:
                continue
            matches = URL_REGEX.findall(text_block)
            for m in matches:
                norm = normalize_domain_from_url(m)
                if norm and not is_free_mail_domain(norm):
                    website = f"https://{norm}"
                    if src not in evidence_sources:
                        evidence_sources.append(src)
                    break
            if website:
                break

        # If no website found and sender has business domain
        if not website and domain and not is_free_mail:
            website = f"https://{domain}"
            if "domain" not in evidence_sources:
                evidence_sources.append("domain")

        # 4. Extract Job Title from Signature
        job_title = None
        if email.signature:
            sig_lines = [line.strip() for line in email.signature.splitlines() if line.strip()]
            for line in sig_lines:
                lower_line = line.lower()
                if any(title_kw in lower_line for title_kw in TITLE_KEYWORDS):
                    # Reasonable length check for job title
                    if len(line) < 80 and not URL_REGEX.search(line) and "@" not in line:
                        job_title = line
                        if "signature" not in evidence_sources:
                            evidence_sources.append("signature")
                        break

        # 5. Extract Company Name
        company_name = None

        # Check explicit prefix in signature or body
        match_pref = COMPANY_PREFIX_REGEX.search(raw_text_for_search)
        if match_pref:
            company_name = match_pref.group("comp").strip()
            if "signature" not in evidence_sources and email.signature:
                evidence_sources.append("signature")

        # Check signature lines for company name candidate
        if not company_name and email.signature:
            sig_lines = [line.strip() for line in email.signature.splitlines() if line.strip()]
            contact_tokens = set(contact_name.lower().split()) if contact_name else set()
            for line in sig_lines:
                clean_line_lower = line.lower()
                # If line is sender name or contains contact name tokens (e.g. sign-off "Random")
                if contact_name and (contact_name.lower() in clean_line_lower or clean_line_lower in contact_tokens):
                    continue
                if "@" in line or URL_REGEX.search(line):
                    continue
                if job_title and job_title.lower() in clean_line_lower:
                    continue
                if any(word in clean_line_lower for word in ["regards", "thanks", "sincerely", "cheers", "tel", "phone", "mobile", "sent from", "best"]):
                    continue
                # For free-mail senders, a single word without company indicators (LLC, Inc, Tech, etc.) is likely a person's name
                if is_free_mail and len(line.split()) == 1 and not any(ind in clean_line_lower for ind in ["corp", "inc", "ltd", "tech", "studio", "labs"]):
                    continue
                if 2 < len(line) < 60:
                    # Check if line looks like a corporate name
                    company_name = line
                    if "signature" not in evidence_sources:
                        evidence_sources.append("signature")
                    break

        # If still no company name and email domain is not free-mail, derive from domain
        if not company_name and domain and not is_free_mail:
            # e.g., acme-technologies.com -> Acme Technologies
            domain_root = domain.split(".")[0]
            clean_comp = " ".join(part.capitalize() for part in re.split(r"[-_]", domain_root))
            company_name = clean_comp
            if "domain" not in evidence_sources:
                evidence_sources.append("domain")

        # Free-mail protection: Never classify free-mail domain as company
        if is_free_mail and not company_name:
            company_name = None

        # 6. Concise Business Summary Generation
        business_summary = self._generate_business_summary(email.subject, email.body, company_name)

        return ExtractedLeadData(
            company_name=company_name,
            contact_name=contact_name,
            job_title=job_title,
            email=sender_email,
            website=website,
            phones=phones,
            business_summary=business_summary,
            evidence_sources=list(set(evidence_sources))
        )

    def _generate_business_summary(self, subject: Optional[str], body: Optional[str], company_name: Optional[str]) -> str:
        """Generates a concise business summary from email subject and body lines."""
        lines = []
        if subject:
            lines.append(f"Subject: {subject}")

        if body:
            # Clean injection patterns
            clean_body = detect_and_neutralize_prompt_injection(body)
            # Find key informative sentences
            sentences = [s.strip() for s in re.split(r"[.\n;]", clean_body) if len(s.strip()) > 15]
            # Take top 3 most informative sentences (avoiding greetings)
            filtered = []
            for s in sentences:
                low = s.lower()
                if low.startswith(("hi ", "hello ", "dear ", "hope you ", "good morning", "good day")):
                    continue
                filtered.append(s)
                if len(filtered) >= 3:
                    break
            if filtered:
                lines.append(". ".join(filtered) + ".")
            elif sentences:
                lines.append(sentences[0] + ".")

        summary = " ".join(lines).strip()
        if not summary:
            return f"Business lead enquiry from {company_name or 'contact'}."
        return summary[:500]

    def _extract_llm(self, email: ParsedEmailData, heur_data: ExtractedLeadData) -> Optional[ExtractedLeadData]:
        """Call Claude API with structured JSON output schema."""
        if not self.llm_client:
            return None

        prompt = f"""You are a specialized business entity extraction model.
Extract structured company and contact information from the following business email.
Do not fabricate information. If an entity is not mentioned or absent, set it to null.
Do not use free consumer email domains (gmail, yahoo, hotmail, etc.) as company names.

EMAIL METADATA:
Sender: {email.sender_name} <{email.sender_email}>
Subject: {email.subject}
Received Date: {email.received_at}

EMAIL BODY:
\"\"\"
{detect_and_neutralize_prompt_injection(email.body or "")}
\"\"\"

SIGNATURE:
\"\"\"
{detect_and_neutralize_prompt_injection(email.signature or "")}
\"\"\"

Return ONLY a valid JSON object matching this schema:
{{
  "company_name": string or null,
  "contact_name": string or null,
  "job_title": string or null,
  "email": string,
  "website": string or null,
  "phones": [string],
  "business_summary": string or null,
  "evidence_sources": [string]
}}"""

        try:
            response = self.llm_client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=1000,
                temperature=settings.LLM_TEMPERATURE,
                system="You extract structured business lead data. Output ONLY valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            raw_json = response.content[0].text.strip()
            # Parse JSON
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
                raw_json = re.sub(r"\s*```$", "", raw_json)
            parsed_dict = json.loads(raw_json)
            return ExtractedLeadData(**parsed_dict)
        except Exception as e:
            logger.error(f"Error in LLM entity extraction: {e}")
            return None
