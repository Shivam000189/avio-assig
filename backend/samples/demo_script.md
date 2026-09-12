# Video Demo Script — AI-Powered Pharmaceutical Customer Complaint Management System (QMS)

**Target Duration**: 5 Minutes  
**Audience**: Quality Assurance Directors, GMP Auditors, Technical Leadership  
**System Under Demo**: FastAPI + Prisma + Neon PostgreSQL + LangGraph AI Pipeline (Gemma-2 & LLaMA-3.3)

---

## Demo Timeline Overview

| Timestamp | Phase / Feature | Primary Action | Key GMP / Technical Takeaway |
| :--- | :--- | :--- | :--- |
| **00:00 - 01:00** | **Step 1**: PDF Ingestion & AI Triage | Upload `complaint_tablet_chipping.pdf` | Content sniffing + automatic entity extraction + risk scoring |
| **01:00 - 02:00** | **Step 2**: Duplicate Detection (Signal Trending) | Upload `complaint_duplicate_chipping.txt` | LLM-as-judge detects duplicate batch `PT-4471-A` (High similarity) |
| **02:00 - 03:00** | **Step 3**: Critical Adverse Event Triage | Submit acute allergic reaction narrative | Fast-track SLA (3 Days), Critical severity, immediate CAPA hold |
| **03:00 - 04:00** | **Step 4**: AI Insights on Saved Complaints | Trigger `POST /complaints/{id}/ai-insights` | Retroactive AI enrichment for manually-logged complaints |
| **04:00 - 05:00** | **Step 5**: Audit Trail & Batch Trend Review | Query `GET /complaints` & batch endpoints | 21 CFR Part 11 transaction integrity & multi-complaint clustering |

---

## Detailed Step-by-Step Script

### Step 1: Uploading Text PDF Complaint (00:00 - 01:00)

#### 🎬 Action:
Upload `samples/files/complaint_tablet_chipping.pdf` to the system via the UI upload button or CLI command:

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_tablet_chipping.pdf"
```

#### 🗣️ Talking Points:
> *"We start with an intake document: a PDF complaint submitted by Farmacia Central Madrid reporting friable, chipped Paracetamol 500mg tablets from batch `PT-4471-A`. Notice that our backend sniffs the binary `%PDF` magic bytes rather than trusting the file extension alone.*
>
> *Without relying on heavy, non-deterministic OCR, `pypdf` extracts the clean text stream and passes it to our 7-node sequential LangGraph pipeline. Gemma-2 extracts all regulatory fields, LLaMA-3.3 assesses ICH Q9 risk, assigning a **Major** severity with a 15-day SLA, drafts an executive QA summary, and formulates a compression tooling inspection CAPA."*

#### 🔍 Expected Output Eyeball:
- `severity`: `"Major"`
- `recommendedSlaDays`: `15`
- `extracted.productName`: `"Paracetamol 500mg Film-Coated Tablets"`
- `extracted.batchNumber`: `"PT-4471-A"`
- `document.filename`: `"complaint_tablet_chipping.pdf"`
- `document.metadata.page_count`: `1`

---

### Step 2: Duplicate Detection & Signal Trending (01:00 - 02:00)

#### 🎬 Action:
A second pharmacy (Farmacia San Jeronimo) reports crumbling tablets for the same batch `PT-4471-A`. Upload `samples/files/complaint_duplicate_chipping.txt`:

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_duplicate_chipping.txt"
```

#### 🗣️ Talking Points:
> *"Now, imagine a second pharmacy in Spain logs a similar incident. When we analyze `complaint_duplicate_chipping.txt`, our new **duplicate_check node** activates.*
>
> *Instead of burdening the system with vector databases or cosine drift, we use an **LLM-as-judge candidate search**. The service queries the database for matching lot numbers and keyword overlap, then feeds the top candidate (`CMP-2026-0001`) to LLaMA-3.3.*
>
> *The AI detects a **High similarity duplicate** on batch `PT-4471-A`. This prevents duplicate investigations, notifies QA of a batch-wide manufacturing trend, and suggests merging the CAPA root cause analysis."*

#### 🔍 Expected Output Eyeball:
```json
"potentialDuplicate": {
  "complaintId": "cuid_001",
  "complaintNumber": "CMP-2026-0001",
  "similarity": "High",
  "explanation": "Matching batch PT-4471-A and identical tablet chipping defect reported.",
  "isPossibleTrend": false
}
```

---

### Step 3: Critical Adverse Event & Pharmacovigilance Escalation (02:00 - 03:00)

#### 🎬 Action:
Submit a severe adverse reaction report via email or raw text:

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/analyze-file" \
  -F "file=@samples/files/complaint_adverse_event.eml"
```

#### 🗣️ Talking Points:
> *"Here we ingest a hospital physician's email (`complaint_adverse_event.eml`) detailing acute pediatric anaphylaxis and dark particulate contamination in Amoxicillin suspension batch `AX-2209-B`.*
>
> *Our RFC-822 email parser extracts the headers directly into metadata. The risk assessment node recognizes immediate patient health harm, scoring it as **Critical** with an accelerated **3-day SLA**.*
>
> *The CAPA node automatically generates an ImmediateCorrection recommendation to quarantine batch `AX-2209-B` and initiate emergency filtration filter inspection."*

#### 🔍 Expected Output Eyeball:
- `severity`: `"Critical"`
- `recommendedSlaDays`: `3`
- `capaActionType`: `"ImmediateCorrection"`
- `source`: `"Email"`
- `document.metadata.subject`: `"URGENT: Adverse event report — Amoxicillin 250mg batch AX-2209-B"`

---

### Step 4: AI Insights on Already-Saved Complaints (03:00 - 04:00)

#### 🎬 Action:
Create a complaint manually without any AI fields (severity=null, aiSummary=null, capa=null):

```bash
# 1. Create manual complaint
curl -X POST "http://localhost:8000/api/v1/complaints" \
  -H "Content-Type: application/json" \
  -d '{
    "complainantName": "Metro Pharmacy",
    "email": "qa@metropharm.com",
    "productName": "Metformin 850mg Tablets",
    "batchNumber": "MF-9021-B",
    "complaintType": "QualityDefect",
    "description": "Patient reported strong chemical smell and mottled brown spots across tablets."
  }'

# 2. Run retroactive AI Insights (replace with returned complaint ID)
curl -X POST "http://localhost:8000/api/v1/complaints/{COMPLAINT_ID}/ai-insights"
```

#### 🗣️ Talking Points:
> *"What about legacy or manually recorded complaints? Our **POST /complaints/{id}/ai-insights** endpoint bridges this gap.*
>
> *We take an existing complaint created with no severity or summary. In one API call, the full LangGraph pipeline executes, evaluates clinical risk, drafts the executive summary, and attaches the recommended CAPA directly to the record in an idempotent transaction."*

---

### Step 5: Dashboard Trending & Seeded Near-Duplicates (04:00 - 05:00)

#### 🎬 Action:
Fetch complaint list and observe batch clustering:

```bash
curl "http://localhost:8000/api/v1/complaints?search=PT-4471-A"
```

#### 🗣️ Talking Points:
> *"Finally, looking at our complaint register, notice `CMP-2026-0001` and `CMP-2026-0005` in our seed dataset. Both represent independent customer reports for batch `PT-4471-A`.*
>
> *With Phase 6 duplicate detection and AI insights, quality engineers immediately see cross-complaint correlations, preventing redundant investigations and accelerating CAPA resolution in full alignment with FDA 21 CFR Part 820 standards."*
