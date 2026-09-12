# Complaint QMS — AI-Powered Customer Complaint Management

Backend for a pharmaceutical QMS complaint module compliant with FDA 21 CFR Part 820 and cGMP standards. Built with **FastAPI**, **Prisma** (PostgreSQL), Pydantic v2 validation, **LangGraph + Groq** sequential AI pipeline, and multi-format document parsing (**PDF / TXT / EML**).

---

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL, GROQ_API_KEY, and optional GEMINI_API_KEY
```

### 4. Push Schema & Generate the Prisma Client

```bash
# Push schema to PostgreSQL database
python -m prisma db push --schema=prisma_schema/schema.prisma

# Generate async Python client
python -m prisma generate --schema=prisma_schema/schema.prisma
```

### 5. Seed Database (Optional)

```bash
python -m scripts.seed
```

### 6. Generate Sample Test PDFs (Optional)

```bash
python samples/files/make_sample_pdfs.py
```

### 7. Run the development server

```bash
uvicorn app.main:create_app --factory --reload
```

Open **http://localhost:8000/docs** to view the interactive OpenAPI Swagger documentation.

### 8. Run tests

```bash
pytest -v
```

All 45+ tests execute deterministically without requiring a live database connection or network/Groq API key.

---

## API Reference

All endpoints are mounted under the `/api/v1` prefix.

| Method | Path | Content-Type | Request Body / Form | Response Codes | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/health` | — | None | `200` | Application health and version check |
| **GET** | `/health/db` | — | None | `200`, `503` | Live PostgreSQL connection health check |
| **POST** | `/complaints/analyze` | `application/json` | `{"text": "...", "source": "Manual"}` | `200`, `422`, `502` | **LangGraph AI Pipeline**: Extracts entities, checks completeness, classifies risk/severity, drafts QA summary, recommends CAPA, and hypothesizes root cause |
| **POST** | `/complaints/analyze-file` | `multipart/form-data` | `file`: `.pdf` / `.txt` / `.eml`<br>`complaint_id` (optional str) | `200`, `413`, `422`, `502` | **Document Upload & AI Triage**: Sniffs content magic bytes, parses text via `pypdf`/email parsers, runs LangGraph pipeline, and optionally attaches document |
| **POST** | `/complaints/from-analysis` | `application/json` | `CreateFromAnalysisRequest` | `201`, `400`, `422`, `500` | **Saved-Complaint Pipeline Bridge**: Atomically commits approved AI analysis as `Complaint` + `ComplaintSummary` + `CAPA` in a single ACID transaction |
| **GET** | `/complaints/stats` | — | None | `200`, `503` | Aggregate metrics (totals, by status, by severity, open by type) |
| **GET** | `/complaints` | — | `skip`, `limit`, `search`, `status`, `severity`, `complaintType`, `created_from`, `created_to` | `200`, `422`, `503` | Paginated complaint list matching filters and search |
| **POST** | `/complaints` | `application/json` | `ComplaintCreate` (JSON) | `201`, `422`, `503` | Submit complaint with auto-generated `CMP-YYYY-NNNN` number |
| **GET** | `/complaints/{id}` | — | None | `200`, `404`, `503` | Retrieve full complaint by ID with relations |
| **PUT** | `/complaints/{id}` | `application/json` | `ComplaintUpdate` (JSON) | `200`, `404`, `422`, `503` | Partial update with audit trail logging |
| **DELETE** | `/complaints/{id}` | — | None | `204`, `404`, `503` | Cascade-delete complaint, documents, CAPA, and summary |
| **GET** | `/complaints/{id}/capa`| — | None | `200`, `404`, `503` | Retrieve CAPA action linked to complaint |
| **PUT** | `/complaints/{id}/capa`| `application/json` | `CapaUpdate` (JSON) | `200`, `404`, `422`, `503` | Upsert CAPA remediation plan for complaint |

---

## Uploading Complaint Documents

The system supports automated document ingestion across PDF, TXT, and RFC-822 EML formats. All uploads enforce:
- **Magic-Byte Sniffing**: Prevents polyglot/mismatched extension attacks (e.g. `%PDF` header check, DOS/PE binary blocking).
- **Max File Size**: 10MB maximum payload (returns `413 Payload Too Large` if exceeded).
- **Substantive Text Verification**: If a PDF has no extractable text layer (e.g. scanned flat image), returns `422` with actionable user guidance.

### 1. Uploading a PDF Document

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_tablet_chipping.pdf"
```

### 2. Uploading an Email (.eml)

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_adverse_event.eml"
```

### 3. Uploading Plain Text (.txt)

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_missing_batch.txt"
```

### 4. Upload & Attach to Existing Complaint (Audit Tracking)

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_wrong_expiry.pdf" \
  -F "complaint_id=clx123abc456"
```

---

## End-to-End Workflow: Ingest → AI Triage → Human Review → Commit

```
 ┌────────────────────────┐
 │ PDF / EML / TXT Upload │  POST /complaints/analyze-file
 └───────────┬────────────┘
             │
             ▼
 ┌────────────────────────┐
 │ Magic Byte Sniffing &  │  app/services/parsers/
 │ Clean Text Extraction  │
 └───────────┬────────────┘
             │
             ▼
 ┌────────────────────────┐
 │ LangGraph AI Engine    │  6-Node Sequential Pipeline
 │ (Gemma-2 & LLaMA-3.3)  │  (Entity, Completeness, Risk, Summary, CAPA, Root Cause)
 └───────────┬────────────┘
             │
             ▼
 ┌────────────────────────┐
 │ Human QA Review in UI  │  QA Specialist inspects extracted fields, edits if needed
 └───────────┬────────────┘
             │
             ▼
 ┌────────────────────────┐
 │ Atomic Transaction DB  │  POST /complaints/from-analysis
 │ Commit (Audit Trail)   │  (Complaint + ComplaintSummary + CAPA in 1 ACID transaction)
 └────────────────────────┘
```

---

## LangGraph AI Pipeline Architecture

```
[START]
   │
   ▼
[1. extract]                (gemma2-9b-it, temp=0.1) -> Extracted entity dictionary
   │
   ▼
[2. completeness]           (gemma2-9b-it, temp=0.0) -> Missing fields check
   │
   ▼
[3. risk_assess]            (llama-3.3-70b-versatile, temp=0.2) -> Severity, reasoning, SLA days
   │
   ▼
[4. summarize_text]         (gemma2-9b-it, temp=0.3) -> Executive QA summary
   │
   ▼
[5. capa]                   (llama-3.3-70b-versatile, temp=0.3) -> Action recommendation & type
   │
   ▼
[6. hypothesize_root_cause] (llama-3.3-70b-versatile, temp=0.3) -> Root cause hypothesis
   │
   ▼
 [END]
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI factory + lifespan + custom 422 handler
│   ├── config.py                   # pydantic-settings configuration (max_upload_mb: 10)
│   ├── constants.py                # Domain Enums (Severity, Status, Types)
│   ├── database.py                 # Prisma client lifecycle
│   ├── exceptions.py               # Custom NotFoundError, GroqUnavailableError
│   ├── agent/                      # LangGraph AI Pipeline
│   │   ├── llm.py                  # ChatGroq client factory + tenacity retry
│   │   ├── state.py                # ComplaintAnalysisState TypedDict
│   │   ├── utils.py                # JSON parsing & self-healing node runner
│   │   ├── graph.py                # 6-node StateGraph + warm compilation
│   │   └── prompts/                # Individual node system prompts
│   ├── routers/
│   │   ├── health.py               # Health & DB ping routes
│   │   ├── analysis.py             # POST /analyze, /analyze-file, /from-analysis
│   │   └── complaints.py           # Full CRUD, Stats, & CAPA routes
│   ├── schemas/
│   │   ├── complaint.py            # Complaint schemas & validators
│   │   ├── capa.py                 # CAPA schemas & validators
│   │   ├── document.py             # Document schemas & validators
│   │   └── analysis.py             # Analysis request/response & upload schemas
│   ├── services/
│   │   ├── parsers/                # Document Ingestion Parsers
│   │   │   ├── __init__.py         # parse_file() dispatcher + content sniffing
│   │   │   ├── base.py             # ParsedDocument & FileParseError
│   │   │   ├── pdf_parser.py       # pypdf text extraction & whitespace cleanup
│   │   │   ├── text_parser.py      # UTF-8 text parser with error replacement
│   │   │   └── email_parser.py     # RFC-822 header & body extractor
│   │   ├── complaint_repository.py # Prisma database repository layer
│   │   └── analysis_service.py     # Graph orchestrator & latency tracker
├── prisma_schema/
│   └── schema.prisma               # Prisma schema definitions
├── samples/
│   ├── sample_inputs.md            # Test scenarios & parsing matrix
│   └── files/                      # Realistic sample complaint files
│       ├── make_sample_pdfs.py     # ReportLab script to generate sample PDFs
│       ├── complaint_tablet_chipping.pdf
│       ├── complaint_wrong_expiry.pdf
│       ├── complaint_adverse_event.eml
│       ├── complaint_missing_batch.txt
│       └── complaint_duplicate_chipping.txt
├── scripts/
│   └── seed.py                     # Idempotent DB seeding script
├── tests/
│   ├── test_health.py              # Health check test suite
│   ├── test_complaints.py          # CRUD & validation test matrix
│   ├── test_analysis.py            # AI graph & routing test suite
│   └── test_upload.py              # Upload & from-analysis test suite
├── postman_collection.json         # Postman/Thunder client test collection
├── .env.example
├── requirements.txt
└── README.md
```
