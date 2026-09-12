# PharmaQMS Complaint Management System

PharmaQMS is a customer complaint intake and triage system for pharmaceutical manufacturing teams. It turns manual narratives and PDF/TXT/EML documents into structured complaint records, risk assessments, CAPA recommendations, and auditable follow-up workflows aligned with FDA 21 CFR Part 820 and cGMP practices.

## Architecture

```text
React + Redux Toolkit + RTK Query
              |
              v
          FastAPI API
        /              \
       v                v
PDF/TXT/EML parser   LangGraph + Groq
       |             7-node pipeline
       +--------->        |
                         v
                    PostgreSQL/Prisma
```

Pipeline order: `extract -> duplicate_check -> completeness -> risk_assess -> summarize_text -> capa -> hypothesize_root_cause`.

## Tech Stack

| Assignment requirement | Implementation |
| --- | --- |
| React + Redux | `frontend/src/components`, `frontend/src/store`, Redux Toolkit, RTK Query |
| FastAPI | `backend/app/main.py` and `backend/app/routers` |
| LangGraph | `backend/app/agent/graph.py` |
| Groq fast model | `gemma2-9b-it` for extraction, completeness, summary, and chat |
| Groq reasoning model | `llama-3.3-70b-versatile` for duplicate, risk, CAPA, and root cause nodes |
| PostgreSQL | Prisma schema in `backend/prisma_schema/schema.prisma` and repository services |
| Google integration | Optional Gemini configuration is supported through `GEMINI_API_KEY`; the current primary AI provider is Groq |

## Bonus Features Implemented

- **Completeness Checker**: identifies missing regulatory intake fields in `backend/app/agent/graph.py`.
- **Duplicate Detection**: compares extracted complaints against batch/product candidates in `backend/app/services/duplicate_service.py`.
- **Risk Classification**: assigns Critical, Major, or Minor severity and an SLA in the risk node.
- **Root Cause Hypothesis**: generates an explicitly labeled investigation hypothesis in the root-cause node.
- **CAPA Recommendation**: recommends corrective or preventive actions and persists them with the complaint.
- **Complaint Summary**: creates an executive summary and linked `ComplaintSummary` record.

## Quick Start

### Backend

See the complete backend setup, Prisma commands, environment variables, API reference, and test instructions in [backend/README.md](backend/README.md).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m prisma generate --schema=prisma_schema/schema.prisma
uvicorn app.main:create_app --factory --reload
```

The API and Swagger UI run at `http://localhost:8000` and `http://localhost:8000/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite proxy sends `/api` and `/health` to `http://localhost:8000`. For deployments, configure `VITE_API_BASE_URL` in `frontend/.env`; local development uses the proxy.

## Screenshots

Replace these TODO placeholders with screenshots from the running application before recording a demo:

- `TODO: screenshots/log-complaint-form.png` - complaint form and AI copilot panel.
- `TODO: screenshots/populated-analysis.png` - populated analysis review state.
- `TODO: screenshots/complaints-list.png` - complaints directory.
- `TODO: screenshots/stats-dashboard.png` - KPI and severity dashboard.

## Repository Layout

- `backend/`: FastAPI, LangGraph, Groq, Prisma, parsers, schemas, and tests.
- `frontend/`: React UI, Redux Toolkit store, RTK Query API layer, and Vite configuration.
