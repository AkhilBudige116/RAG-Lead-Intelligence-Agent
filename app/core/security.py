import re
from typing import Any

# Characters that trigger formula execution in spreadsheet software (CSV/Excel)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Known prompt injection pattern signatures
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"disregard\s+the\s+above", re.IGNORECASE),
    re.compile(r"you\s+must\s+classify\s+(this\s+)?as", re.IGNORECASE),
    re.compile(r"new\s+instruction\s*:", re.IGNORECASE),
    re.compile(r"output\s+only\s+the\s+following", re.IGNORECASE),
    re.compile(r"override\s+system\s+prompt", re.IGNORECASE),
]


def sanitize_spreadsheet_cell(val: Any) -> Any:
    """
    Prevents CSV / Excel formula injection (CSV Injection / CWE-1236).
    If a string cell starts with =, +, -, @, prepend a single quote '.
    """
    if val is None:
        return ""
    s_val = str(val).strip()
    if s_val and s_val.startswith(FORMULA_PREFIXES):
        return "'" + s_val
    return val


def detect_and_neutralize_prompt_injection(text: str) -> str:
    """
    Detects attempts to hijack LLM system instructions inside untrusted email content.
    Flags or neutralizes obvious injection patterns.
    """
    if not text:
        return ""

    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(sanitized):
            sanitized = pattern.sub("[REDACTED_SUSPICIOUS_PROMPT]", sanitized)

    # Escape XML/markdown delimiter attempts if present
    sanitized = sanitized.replace("<SYSTEM>", "[SYSTEM]").replace("</SYSTEM>", "[/SYSTEM]")
    sanitized = sanitized.replace("<INSTRUCTION>", "[INSTRUCTION]").replace("</INSTRUCTION>", "[/INSTRUCTION]")
    return sanitized


def sanitize_input_text(text: str, max_length: int = 15000) -> str:
    """
    General string sanitizer limiting length and removing control characters.
    """
    if not text:
        return ""
    # Strip null bytes and non-printable control characters except newline and tab
    cleaned = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or ord(ch) >= 32)
    return cleaned[:max_length].strip()
