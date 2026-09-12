# PharmaQMS Frontend

React and TypeScript frontend for the pharmaceutical customer complaint QMS. It provides complaint intake, PDF/TXT/EML analysis, human review, complaint search, status updates, AI insights, and KPI dashboards.

## Prerequisites

- Node.js 20+
- Backend running at `http://localhost:8000`
- PostgreSQL and Groq configuration as described in [backend/README.md](../backend/README.md)

## Setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/health` to the local backend. For a deployed frontend, set `VITE_API_BASE_URL` in `.env`; local development uses the Vite proxy.

## Commands

```powershell
npm run build
npm run lint
```

## Structure

- `src/api/`: shared API response and payload types.
- `src/components/`: complaint form, AI assistant, list, detail modal, and dashboard views.
- `src/store/`: Redux Toolkit slices and RTK Query endpoints for application and server state.
- `src/App.tsx`: layout composition and view selection.
