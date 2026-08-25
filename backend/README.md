# Email Threat Detection Backend

FastAPI backend for the SIH 2026 **AI-Powered Email Threat Detection, GeoLocation and Forensic Intelligence Platform**.

This version provides API health checking, local `.eml` parsing, deterministic rule-based risk scoring, and optional Gemini semantic analysis. It does not yet implement database storage, geolocation, graphs, or reports.

## Prerequisites

- Python 3.10 or newer

## Run locally

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /api/health` returns `{ "status": "ok" }`.
- `POST /api/analyze` accepts a multipart form field named `file` containing an `.eml` file. It runs parsing, technical indicators, deterministic scoring, optional Gemini semantic analysis, cached public-IP intelligence, relay-timeline construction, and threat-graph generation. IPs observed in the message are labeled `observed_email`; DNS-derived URL/domain infrastructure (only used when the EML contains no IP evidence) is labeled `dns_resolved`. Relay timeline events are based on Received headers and do not represent an attacker's physical path. IP data is labeled **Probable Infrastructure Location**; it does not identify an attacker's physical location.

Example upload:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/analyze -Form @{ file = Get-Item .\sample.eml }
```

## Environment variables

Copy `.env.example` to `.env` to enable Gemini semantic analysis. The real `GEMINI_API_KEY` must stay in `.env`, which is ignored by Git; never place it in frontend code or commit it. If the key is missing or Gemini fails, `ai_analysis.result` is `null` and the deterministic analysis still returns.

## Case storage

SQLite case storage is available through `POST /api/cases`, `GET /api/cases`, and `GET /api/cases/{case_id}`. A stored case contains its ID, timestamp, filename, deterministic result summary, and indicators. The local database is ignored by Git and does not store API keys or other secrets.

## PDF reports

`GET /api/reports/{case_id}/pdf` generates a professional forensic PDF report from a stored case. Include the optional `analysis` snapshot when creating a case to retain full email, authentication, network, AI, relay, and graph evidence for the report. Reports never include API keys or secrets.
