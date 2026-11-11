import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    keywords = Column(JSON, default=list)
    examples = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    companies = relationship("Company", back_populates="sector")
    classifications = relationship("Classification", back_populates="sector")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    normalized_name = Column(String(255), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    website = Column(String(255), nullable=True)
    sector_id = Column(String(50), ForeignKey("sectors.id"), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    classification_reason = Column(Text, nullable=True)
    status = Column(String(50), default="needs_review", index=True)  # 'classified', 'needs_review', 'merged'
    merged_into_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    sector = relationship("Sector", back_populates="companies")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    emails = relationship("Email", back_populates="company")
    classifications = relationship("Classification", back_populates="company", cascade="all, delete-orphan")
    merged_into = relationship("Company", remote_side=[id], backref="merged_children")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(100), nullable=True)
    email_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    emails = relationship("Email", back_populates="contact")


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(String(64), primary_key=True, index=True)  # UUID
    filename = Column(String(255), nullable=False)
    total_emails = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String(50), default="pending", index=True)  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    emails = relationship("Email", back_populates="batch")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    batch_id = Column(String(64), ForeignKey("upload_batches.id"), nullable=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True, index=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    signature = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True)
    source_file = Column(String(255), nullable=True)
    raw_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256
    evidence_sources = Column(JSON, default=list)  # ["signature", "body", "domain"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("UploadBatch", back_populates="emails")
    contact = relationship("Contact", back_populates="emails")
    company = relationship("Company", back_populates="emails")


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    sector_id = Column(String(50), ForeignKey("sectors.id"), nullable=True, index=True)
    confidence = Column(Float, nullable=False)
    llm_confidence = Column(Float, nullable=True)
    top_retrieval_similarity = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    evidence = Column(JSON, default=list)
    retrieved_sector_ids = Column(JSON, default=list)
    model_version = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="classifications")
    sector = relationship("Sector", back_populates="classifications")


class DuplicateLog(Base):
    __tablename__ = "duplicate_log"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    kept_company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    merged_company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    rule = Column(String(100), nullable=False)  # 'email_exact', 'domain_match', 'fuzzy_name'
    details = Column(JSON, default=dict)
    active = Column(Boolean, default=True, index=True)  # False if undone
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    kept_company = relationship("Company", foreign_keys=[kept_company_id])
    merged_company = relationship("Company", foreign_keys=[merged_company_id])
