# RAG-Based Lead Segregation Agent

An enterprise-grade, production-ready AI platform designed to ingest business emails in multiple formats (.eml, .msg, .mbox, CSV, JSON), extract structured company & contact information, retrieve domain knowledge via a dynamic 13-sector RAG knowledge base, classify leads using Anthropic Claude with strict structured JSON output, evaluate confidence with a dual-factor decision gate, detect and consolidate duplicates via multi-rule fuzzy matching with audit trails, route low-confidence leads to a human-in-the-loop review queue, display rich business intelligence analytics on a React dashboard, and export reports in CSV/XLSX with formula-injection defenses.

---

## Architecture Blueprint

```
                      Business Email Input
          (.eml, .msg, .mbox, CSV, Authorized JSON API)
                                │
                                ▼
                   [File Validation & Ingestion]
        (MIME check, max 25MB, duplicate SHA-256 hash check)
                                │
                                ▼
                    [Email Body & Header Parser]
    (HTML tag stripping, forwarded chain parsing, signature separation)
                                │
                                ▼
               [LLM + Regex Entity Extraction Service]
 (Company, Contact Name, Title, Email, Website, Standardized Phone, Summary)
                                │
                                ▼
           [Dynamic RAG Knowledge Base & Vector Retrieval]
 (39 Chunks across 13 Sectors, FastEmbed BGE-Small-EN, Top-5 Cosine Similarity)
                                │
                                ▼
                [AI Sector Classification Engine]
    (Anthropic Claude / Deterministic Fallback, Strict JSON Output, Temp 0)
                                │
                                ▼
                    [Confidence Decision Gate]
          final_confidence = (0.6 * LLM) + (0.4 * RAG_Sim)
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
        >= 0.75: Classified           < 0.75: Needs Review
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
               [Intelligent Duplicate Detection]
         Rule 1: Normalized Exact Email Match (Contact Level)
         Rule 2: Same Business Domain Match (Company Level)
         Rule 3: RapidFuzz token_set_ratio (>=90 Auto-merge, 80-90 Flag)
                                │
                                ▼
                  [Relational Database Storage]
        (Supabase PostgreSQL / SQLite, Audit Logs, Undo Merge)
                                │
                                ▼
             [Enterprise React SaaS Analytics Dashboard]
     (KPI Cards, Recharts Analytics, TanStack Table, Detail Drawer, Exports)
```

---

## Key Features

1. **Multi-Format Ingestion**: Supports `.eml`, `.msg`, `.mbox`, CSV files, and direct authorized JSON payloads with duplicate hash detection and background batch processing.
2. **Entity Extraction**: Extracts company, contact person, job title, email, website, normalized phone numbers (via `phonenumbers`), and generated business summaries.
3. **Free-Mail Domain Safety**: Comprehensive exclusion list (`gmail.com`, `yahoo.com`, `hotmail.com`, etc.) preventing consumer domains from being misclassified as companies.
4. **13 Predefined Industry Sectors**:
   - IT & Software
   - Healthcare & Pharmaceuticals
   - Education & EdTech
   - Real Estate & Construction
   - Retail & E-commerce
   - Manufacturing
   - Finance & Insurance
   - Hospitality & Tourism
   - Logistics & Transportation
   - Marketing & Advertising
   - Food & Beverage
   - Professional Services
   - Other / Unknown
5. **3-Chunk Vector Architecture**: Each sector is indexed as Description, Keywords, and Example Businesses into ChromaDB / Supabase pgvector.
6. **Dual-Factor Confidence Scoring**:
   $$\text{final\_confidence} = (0.6 \times \text{llm\_confidence}) + (0.4 \times \text{top\_retrieval\_similarity})$$
   - $\ge 0.75$: Automatically Classified
   - $0.50 \le x < 0.75$: Routed to Human Review Queue
   - $< 0.50$: Routed to Needs Review / Unknown
7. **3-Rule Duplicate Detection**:
   - **Rule 1**: Normalized exact email match updates existing contact and increments email count.
   - **Rule 2**: Matching business domain attaches new contacts to existing company.
   - **Rule 3**: RapidFuzz fuzzy name similarity: $\ge 90$ with same/missing domain auto-merges; $80 - 90$ with differing domains flags for reviewer comparison.
8. **Consolidation & Undo Merge**: Preserves highest confidence sector, flags sector conflicts, maintains audit records in `duplicate_log`, and provides full **Undo Merge** reversion.
9. **Human-in-the-Loop Review System**: Interactive review queue allowing analysts to accept AI suggestions, change sectors, record notes, and optionally append confirmed companies to the RAG knowledge base.
10. **Security & Formula Protection**: Sanitizes cells against CSV injection (`=`, `+`, `-`, `@`), defends against prompt injection, and sanitizes untrusted email bodies.

---

## Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS v4, Lucide React, Recharts, Axios, React Router v6.
- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn.
- **AI / LLM**: Anthropic Claude API (`claude-3-5-sonnet-20241022`) with structured JSON schema and deterministic mock fallback engine for offline testing.
- **Embeddings**: `BAAI/bge-small-en` via FastEmbed ONNX runtime.
- **Vector Database**: ChromaDB (local persistent development) and Supabase pgvector (production) via common `VectorRepositoryInterface`.
- **Relational Database**: Supabase PostgreSQL / SQLite fallback for zero-dependency local dev.
- **Duplicate Detection**: RapidFuzz `token_set_ratio` with corporate suffix stripping.
- **Export**: Pandas & OpenPyXL with multi-sheet workbook generation and formula injection escaping.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js v18+ and npm
- Docker & Docker Compose (optional for containerized deployment)

### 1. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configurable environment variables:
```env
LLM_API_KEY=your_anthropic_api_key_here  # Leave empty for deterministic local mock mode
LLM_MODEL=claude-3-5-sonnet-20241022
EMBEDDING_MODEL=BAAI/bge-small-en
EMBEDDING_PROVIDER=fastembed
VECTOR_STORE=chroma
DATABASE_URL=sqlite:///./data/lead_agent.db
CONFIDENCE_THRESHOLD=0.75
```

### 2. Backend Setup
Create and activate virtual environment, install dependencies, and seed sectors:
```bash
# Create venv with Python 3.11
python -m venv .venv

# Activate venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database and seed sectors
python -m app.db.seed

# Start FastAPI backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Swagger API docs will be live at: `http://localhost:8000/docs`

### 3. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at: `http://localhost:5173`

---

## Docker Deployment

To launch the complete full-stack platform using Docker Compose:
```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:3000`
- FastAPI Backend: `http://localhost:8000`
- API Health Check: `http://localhost:8000/api/health`

---

## Testing & Verification

### Running Automated Test Suite
Run the 22 automated unit and integration tests:
```bash
pytest tests/ -v
```
Tests include:
- `tests/integration/test_api.py`: Health, sector listing, JSON email ingestion, lead retrieval, stats, CSV/Excel export.
- `tests/unit/test_ingestion.py`: Multi-format parsing, MIME validation, quote stripping, signature separation, free-mail exclusion.
- `tests/unit/test_extraction.py`: Company, domain, phone normalization, deterministic lead extraction.
- `tests/unit/test_rag.py`: FastEmbed BGE-small-en embeddings, ChromaDB top-5 retrieval, cosine similarity.
- `tests/unit/test_classification.py`: Dual-factor confidence gate, threshold routing, caching.
- `tests/unit/test_dedup.py`: Rules 1, 2, and 3 duplicate detection and consolidation.
- `tests/unit/test_export.py`: CSV injection protection and multi-sheet workbook generation.

### Running Evaluation Framework
Run the regression benchmark on the 210 labelled email dataset:
```bash
python eval/evaluate.py --split test --min-accuracy 0.80
```
#### Benchmark Results on Held-out Test Split:
- **Overall Classification Accuracy**: **87.23%** (Target: $\ge 80.0\%$) - **PASS**
- **Duplicate Detection Recall**: **100.0%**
- **Email Extraction Accuracy**: **100.0%**
- **Review Suggestion Accuracy**: **90.9%**
- **Average Processing Latency**: **25.89 ms / email**
- **Estimated Cost per 100 Emails**: **$0.00** (Local FastEmbed ONNX engine)

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health and configuration check |
| `POST` | `/api/uploads` | Upload multi-format email batch (.eml, .msg, .mbox, .csv, .json) |
| `POST` | `/api/emails/ingest` | Direct JSON email payload ingestion |
| `GET` | `/api/batches` | List batch processing history |
| `GET` | `/api/batches/{id}` | Real-time batch processing progress and counts |
| `GET` | `/api/leads` | Paginated lead directory with search, sector, status, and confidence filters |
| `GET` | `/api/leads/{id}` | Complete lead details, RAG trace, confidence formula, and email history |
| `PATCH` | `/api/leads/{id}/sector` | Human reviewer sector confirmation/correction |
| `GET` | `/api/stats` | Overview dashboard KPI metrics and Recharts chart datasets |
| `GET` | `/api/sectors` | List active sectors |
| `POST` | `/api/sectors` | Create and index a new industry sector |
| `PATCH` | `/api/sectors/{id}` | Update sector definition and refresh vector index |
| `DELETE` | `/api/sectors/{id}` | Safely deactivate a sector |
| `POST` | `/api/sectors/reindex-all`| Trigger vector re-indexing across all sectors |
| `GET` | `/api/review/queue` | Retrieve all pending Needs Review leads |
| `POST` | `/api/review/{id}/action`| Process reviewer decision (accept suggestion or override sector) |
| `GET` | `/api/duplicates` | Retrieve potential duplicate pairs and confirmed merge history |
| `POST` | `/api/duplicates/merge` | Manually confirm duplicate merge |
| `POST` | `/api/duplicates/reject` | Reject potential duplicate flag |
| `POST` | `/api/duplicates/undo` | Undo a previous merge, restoring original company records |
| `GET` | `/api/export?format=csv\|xlsx` | Download filtered lead records with formula injection protection |

---

## Production Security Notes

- **Untrusted Input Sanitation**: All email bodies, subjects, and signatures are sanitized to neutralize prompt injection attacks.
- **Formula Injection Defense**: All exported cells in CSV and Excel files starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with `'` to prevent DDE / command execution.
- **Confidential Credentials**: API keys are managed exclusively via environment variables and never logged or exposed in frontend responses.
