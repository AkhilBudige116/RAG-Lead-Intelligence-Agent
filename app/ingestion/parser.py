import os
import re
import io
import json
import mailbox
import datetime
from email import policy
from email.parser import BytesParser
from typing import List, Dict, Any, Optional, Tuple, Union
from bs4 import BeautifulSoup
import pandas as pd
from app.ingestion.validation import compute_sha256
from app.core.logging import logger

try:
    import extract_msg
except ImportError:
    extract_msg = None


SIGNATURE_SEPARATORS = [
    re.compile(r"^--\s*$", re.MULTILINE),
    re.compile(r"^(thanks\s+(&|and)\s+regards|best\s+regards|warm\s+regards|kind\s+regards|regards|sincerely|cheers|thanks),?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^with\s+warm\s+regards,?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^sent\s+from\s+my\s+(iphone|android|galaxy|ipad|device)", re.IGNORECASE | re.MULTILINE),
]

QUOTED_REPLY_PATTERNS = [
    re.compile(r"^-+\s*Original Message\s*-+.*", re.IGNORECASE | re.DOTALL),
    re.compile(r"^On\s+.+,\s*.+\s+at\s+.+wrote:.*", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^\*From:\*.*", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^From:\s+.*", re.IGNORECASE | re.DOTALL | re.MULTILINE),
]

FORWARDED_ORIGIN_PATTERN = re.compile(
    r"(?:From|Sender):\s*(?:(?P<name>[^<\n]+?)\s*<)?(?P<email>[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?",
    re.IGNORECASE
)


class ParsedEmailData:
    def __init__(
        self,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        signature: Optional[str] = None,
        received_at: Optional[datetime.datetime] = None,
        source_file: str = "unknown",
        raw_hash: str = "",
        raw_text: str = "",
        evidence_sources: Optional[List[str]] = None
    ):
        self.sender_name = sender_name.strip() if sender_name else None
        self.sender_email = sender_email.strip().lower() if sender_email else None
        self.subject = subject.strip() if subject else None
        self.body = body.strip() if body else ""
        self.signature = signature.strip() if signature else None
        self.received_at = received_at or datetime.datetime.utcnow()
        self.source_file = source_file
        self.raw_hash = raw_hash
        self.raw_text = raw_text
        self.evidence_sources = evidence_sources or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_name": self.sender_name,
            "sender_email": self.sender_email,
            "subject": self.subject,
            "body": self.body,
            "signature": self.signature,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "source_file": self.source_file,
            "raw_hash": self.raw_hash,
            "evidence_sources": self.evidence_sources,
        }


def strip_html_tags(html_content: str) -> str:
    """Removes HTML markup while preserving paragraph line breaks."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    # Replace breaks and paragraphs with newlines
    for br in soup.find_all(["br", "p", "div"]):
        br.append("\n")
    return soup.get_text()


def separate_body_and_signature(text: str) -> Tuple[str, Optional[str]]:
    """Splits plain text email into body and signature block."""
    if not text:
        return "", None

    best_split_idx = -1
    for sep_pat in SIGNATURE_SEPARATORS:
        match = sep_pat.search(text)
        if match:
            # Look for the earliest occurrence that isn't at the very start
            idx = match.start()
            if idx > 20 and (best_split_idx == -1 or idx < best_split_idx):
                best_split_idx = idx

    if best_split_idx != -1:
        body = text[:best_split_idx].strip()
        signature = text[best_split_idx:].strip()
        return body, signature

    return text.strip(), None


def remove_quoted_replies(text: str) -> Tuple[str, Optional[Tuple[str, str]]]:
    """
    Strips quoted chain history while checking if this was a forwarded email chain.
    Returns (cleaned_text, (forwarded_name, forwarded_email) if found).
    """
    if not text:
        return "", None

    forwarded_sender = None
    cleaned = text

    # Check for original sender in forwarded header
    for fwd_pat in [re.compile(r"---------- Forwarded message ---------.*?\n(.*?)(?:\n\n|\Z)", re.DOTALL | re.IGNORECASE),
                    re.compile(r"-----Original Message-----.*?\n(.*?)(?:\n\n|\Z)", re.DOTALL | re.IGNORECASE)]:
        fwd_match = fwd_pat.search(text)
        if fwd_match:
            header_block = fwd_match.group(1)
            sender_match = FORWARDED_ORIGIN_PATTERN.search(header_block)
            if sender_match:
                name = sender_match.group("name")
                email = sender_match.group("email")
                if email:
                    forwarded_sender = (name.strip() if name else None, email.strip().lower())

    # Cut off quoted reply lines starting with '>' or standard reply headers
    lines = []
    for line in cleaned.splitlines():
        if line.strip().startswith(">"):
            continue
        if re.match(r"^On\s+.+wrote:\s*$", line.strip(), re.IGNORECASE):
            break
        if re.match(r"^-+\s*Original Message\s*-+$", line.strip(), re.IGNORECASE):
            break
        if re.match(r"^---------- Forwarded message ---------", line.strip(), re.IGNORECASE):
            break
        lines.append(line)

    return "\n".join(lines).strip(), forwarded_sender


def parse_eml_bytes(content: bytes, filename: str = "upload.eml") -> ParsedEmailData:
    """Parses standard RFC822 / MIME .eml bytes."""
    raw_hash = compute_sha256(content)
    msg = BytesParser(policy=policy.default).parsebytes(content)

    sender = msg.get("from", "")
    sender_name = ""
    sender_email = ""
    if sender:
        parsed_from = FORWARDED_ORIGIN_PATTERN.search(str(sender))
        if parsed_from:
            sender_name = parsed_from.group("name") or ""
            sender_email = parsed_from.group("email") or ""
        else:
            sender_email = str(sender)

    subject = msg.get("subject", "")
    date_header = msg.get("date")
    received_at = None
    if date_header:
        try:
            received_at = pd.to_datetime(str(date_header)).to_pydatetime()
        except Exception:
            received_at = datetime.datetime.utcnow()

    # Extract body content
    body_text = ""
    body_part = msg.get_body(preferencelist=('plain', 'html'))
    if body_part:
        charset = body_part.get_content_charset() or "utf-8"
        try:
            payload = body_part.get_content()
            if isinstance(payload, str):
                body_text = payload
            else:
                body_text = payload.decode(charset, errors="replace")
        except Exception:
            body_text = body_part.as_string()
    else:
        # Fallback to string payload
        payload = msg.get_payload()
        if isinstance(payload, str):
            body_text = payload
        elif isinstance(payload, list):
            for part in payload:
                if hasattr(part, "get_content_type") and part.get_content_type() == "text/plain":
                    body_text += part.get_payload(decode=True).decode("utf-8", errors="replace")

    if "<html" in body_text.lower() or "<div" in body_text.lower() or "<p" in body_text.lower():
        body_text = strip_html_tags(body_text)

    cleaned_body, forwarded_sender = remove_quoted_replies(body_text)
    if forwarded_sender and forwarded_sender[1]:
        # Original sender found in forward
        sender_name = forwarded_sender[0] or sender_name
        sender_email = forwarded_sender[1]

    body, signature = separate_body_and_signature(cleaned_body)
    evidence_sources = ["body"]
    if signature:
        evidence_sources.append("signature")

    return ParsedEmailData(
        sender_name=sender_name,
        sender_email=sender_email,
        subject=subject,
        body=body,
        signature=signature,
        received_at=received_at,
        source_file=filename,
        raw_hash=raw_hash,
        raw_text=body_text,
        evidence_sources=evidence_sources
    )


def parse_msg_bytes(content: bytes, filename: str = "upload.msg") -> ParsedEmailData:
    """Parses Outlook .msg file bytes using extract_msg."""
    raw_hash = compute_sha256(content)
    if extract_msg is None:
        raise ImportError("extract_msg library is required for parsing .msg files.")

    msg = extract_msg.Message(io.BytesIO(content))
    sender_name = msg.sender or ""
    sender_email = ""
    if hasattr(msg, "senderEmail"):
        sender_email = msg.senderEmail or ""
    if not sender_email and sender_name:
        parsed = FORWARDED_ORIGIN_PATTERN.search(sender_name)
        if parsed:
            sender_name = parsed.group("name") or sender_name
            sender_email = parsed.group("email") or ""

    subject = msg.subject or ""
    body_text = msg.body or ""
    if not body_text and hasattr(msg, "htmlBody") and msg.htmlBody:
        body_text = strip_html_tags(msg.htmlBody.decode("utf-8", errors="replace"))

    received_at = msg.date or datetime.datetime.utcnow()

    cleaned_body, forwarded_sender = remove_quoted_replies(body_text)
    if forwarded_sender and forwarded_sender[1]:
        sender_name = forwarded_sender[0] or sender_name
        sender_email = forwarded_sender[1]

    body, signature = separate_body_and_signature(cleaned_body)
    evidence_sources = ["body"]
    if signature:
        evidence_sources.append("signature")

    return ParsedEmailData(
        sender_name=sender_name,
        sender_email=sender_email,
        subject=subject,
        body=body,
        signature=signature,
        received_at=received_at,
        source_file=filename,
        raw_hash=raw_hash,
        raw_text=body_text,
        evidence_sources=evidence_sources
    )


def parse_mbox_bytes(content: bytes, filename: str = "upload.mbox") -> List[ParsedEmailData]:
    """Parses mbox format containing multiple messages."""
    import tempfile
    results = []
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mbox") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        box = mailbox.mbox(tmp_path)
        for idx, msg in enumerate(box):
            msg_bytes = msg.as_bytes()
            item = parse_eml_bytes(msg_bytes, filename=f"{filename}#item{idx+1}")
            results.append(item)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return results


def parse_csv_bytes(content: bytes, filename: str = "upload.csv") -> List[ParsedEmailData]:
    """Parses CSV with email headers."""
    results = []
    df = pd.read_csv(io.BytesIO(content))
    # Standardize column names to lowercase stripped
    col_map = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df.rename(columns=col_map, inplace=True)

    for idx, row in df.iterrows():
        sender_name = str(row.get("sender_name") or row.get("name") or row.get("contact_name") or "")
        sender_email = str(row.get("sender_email") or row.get("email") or row.get("from") or "")
        subject = str(row.get("subject") or row.get("title") or "")
        raw_body = str(row.get("body") or row.get("message") or row.get("content") or "")
        sig = str(row.get("signature") or "")

        row_content_str = f"{sender_name}|{sender_email}|{subject}|{raw_body}|{idx}"
        raw_hash = compute_sha256(row_content_str.encode("utf-8"))

        body, detected_sig = separate_body_and_signature(raw_body)
        signature = sig or detected_sig

        evidence_sources = ["body"]
        if signature:
            evidence_sources.append("signature")

        results.append(ParsedEmailData(
            sender_name=sender_name if sender_name and sender_name != "nan" else None,
            sender_email=sender_email if sender_email and sender_email != "nan" else None,
            subject=subject if subject and subject != "nan" else None,
            body=body,
            signature=signature,
            received_at=datetime.datetime.utcnow(),
            source_file=filename,
            raw_hash=raw_hash,
            raw_text=raw_body,
            evidence_sources=evidence_sources
        ))
    return results


def parse_json_content(content: Union[str, bytes, dict, list], filename: str = "upload.json") -> List[ParsedEmailData]:
    """Parses JSON email object or array of email objects."""
    if isinstance(content, bytes):
        data = json.loads(content.decode("utf-8"))
    elif isinstance(content, str):
        data = json.loads(content)
    else:
        data = content

    if isinstance(data, dict):
        data = [data]

    results = []
    for idx, item in enumerate(data):
        raw_hash = item.get("raw_hash") or compute_sha256(json.dumps(item, sort_keys=True).encode("utf-8"))
        raw_body = item.get("body", "")
        sig = item.get("signature")
        body, detected_sig = separate_body_and_signature(raw_body)
        signature = sig or detected_sig

        evidence_sources = item.get("evidence_sources") or ["body"]
        if signature and "signature" not in evidence_sources:
            evidence_sources.append("signature")

        results.append(ParsedEmailData(
            sender_name=item.get("sender_name") or item.get("contact_name"),
            sender_email=item.get("sender_email") or item.get("email"),
            subject=item.get("subject"),
            body=body,
            signature=signature,
            received_at=datetime.datetime.utcnow(),
            source_file=filename,
            raw_hash=raw_hash,
            raw_text=raw_body,
            evidence_sources=evidence_sources
        ))
    return results


def parse_file(filename: str, content: bytes) -> List[ParsedEmailData]:
    """Unified file parser routing by extension."""
    _, ext = os.path.splitext(filename.lower())
    if ext == ".eml":
        return [parse_eml_bytes(content, filename)]
    elif ext == ".msg":
        return [parse_msg_bytes(content, filename)]
    elif ext == ".mbox":
        return parse_mbox_bytes(content, filename)
    elif ext == ".csv":
        return parse_csv_bytes(content, filename)
    elif ext == ".json":
        return parse_json_content(content, filename)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
