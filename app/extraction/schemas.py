from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class ExtractedLeadData(BaseModel):
    company_name: Optional[str] = Field(default=None, description="Extracted corporate or business name")
    contact_name: Optional[str] = Field(default=None, description="Sender or contact person's full name")
    job_title: Optional[str] = Field(default=None, description="Contact person's business title")
    email: str = Field(description="Normalized business or sender email address")
    website: Optional[str] = Field(default=None, description="Company website URL or domain")
    phones: List[str] = Field(default_factory=list, description="Standardized phone numbers in international format")
    business_summary: Optional[str] = Field(default=None, description="Concise summary of products, services, or business activities")
    evidence_sources: List[str] = Field(default_factory=list, description="Tags indicating where data was found: signature, body, domain")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if not v:
            raise ValueError("Email cannot be empty")
        return v.strip().lower()

    @field_validator("company_name")
    @classmethod
    def clean_company_name(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip().lower() in ("null", "none", "n/a", "unknown"):
            return None
        return v.strip()


class ClassificationResult(BaseModel):
    sector: str = Field(description="Matched sector name from active sectors or 'Needs Review'")
    confidence: float = Field(ge=0.0, le=1.0, description="Model self-assessed confidence score between 0 and 1")
    reason: str = Field(description="Evidence-based rationale explaining the classification decision")
    evidence: List[str] = Field(default_factory=list, description="Specific phrases or keywords from email supporting the sector")
