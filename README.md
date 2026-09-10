# ControlCheck AI 2.0

**AI Project Control Assistant / Project Intelligence Assistant**

Upload project data → Ingestion Agent reads, maps, validates and publishes a semantic snapshot → ask → inspect insights → export a report.

This is a new, independent development scaffold. It does not import, migrate or modify the old ControlCheck applications.

## Run locally (Windows)

Prerequisites: Python 3.11+, Node.js 22.12+, and Java 17+ for direct MPP or Primavera P6 XER import. CSV/XLSX/Project XML do not require Java.

```powershell
cd E:/project/ControlCheck-V2
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
npm.cmd ci
```

Terminal 1 — API:

```powershell
.venv/Scripts/python.exe -m uvicorn controlcheck.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

Terminal 2 — web:

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs. Keep both terminals running. SQLite is created automatically in data/local; project data survives restarts. No API key is needed. `.env.example` documents the optional database path; this scaffold reads process environment variables, not .env files automatically.

## First walkthrough

1. Create a project, choose IDR and reporting date **2026-09-08** for the synthetic sample.
2. Open Data Center, choose data/samples/project-snapshot.csv (or the corresponding XLSX), then click **Analisis project data**.
3. Review the agent receipt and open Overview.
4. Use **Advanced data review** only when the agent asks for attention or when you need manual control.
5. Ask **Bagaimana kondisi proyek saya?**, then **Aktivitas apa yang terlambat?**
6. Open Reports and download the Markdown report.
7. Upload quality-errors.csv to exercise blocking validation without replacing approved data.

Use one complete leaf-activity snapshot per upload. A new publication replaces the active view rather than merging files. Do not combine WBS summaries and their child rows. CSV is UTF-8 with comma, semicolon or tab delimiter. Data Center previews the first rows, suggests a header row, lists XLSX sheets and requires explicit date (`YYYY-MM-DD`, `DD/MM/YYYY` or `MM/DD/YYYY`), decimal and progress-scale choices. Formula cells must first be converted to values. Currency: one project currency; no symbols or thousands separators in numeric cells. Limits: CSV/XLSX 5 MB; MPP/XER 50 MB; 10,000 rows/activities; 100 columns.

## What works / what is a foundation

- Working: project creation/selection, automatic agent ingestion for CSV/XLSX/MPP/Project XML/Primavera P6 XER, persisted uploads, advanced editable mapping, quality gate, immutable normalized snapshot versions with per-publication reporting dates, consecutive-period comparison, deterministic Forecast Readiness gate, deterministic schedule/progress/cost analytics, critical/milestone and dependency-impact analysis when supplied by the schedule, evidence-backed rule insights, optional SumoPod Grounded AI with validated citations, conversation history and Markdown export.
- Interfaces prepared: XER importer, forecast method/range calculation and agent action proposals.
- Not connected: forecast date/probability calculation, production authentication, tenant permissions, queued ingestion, PDF export and autonomous actions.

Without a configured key, the assistant is explicitly labelled **Analitik lokal**. With `SUMOPOD_API_KEY`, the selected SumoPod model receives bounded approved snapshot context and must return validated row citations. Read the production gates before deploying to shared infrastructure.

## Repository

```text
apps/
  web/                  React + TypeScript workspace
  api/controlcheck/     FastAPI + domain modules + SQLite repository
packages/contracts/     OpenAPI and semantic contract
data/samples/           Synthetic CSV/XLSX fixtures
docs/                   Product, architecture, screens, roadmap, validation
infra/                  Local/production boundary notes
scripts/                Contract export
tests/                  Domain and HTTP journey tests
```

## Verify

```powershell
.venv/Scripts/python.exe -m pytest tests -q
npm.cmd run build
.venv/Scripts/python.exe scripts/export_contracts.py
```

See [PRD](docs/PRD.md), [Architecture](docs/ARCHITECTURE.md), [Screen inventory](docs/SCREEN_INVENTORY.md), [Roadmap](docs/ROADMAP.md), [Implementation plan](docs/IMPLEMENTATION_PLAN.md), and [Validation](docs/VALIDATION.md).

Before real multiuser deployment: authentication, authorization, migrations, original-file retention/deletion, audit, backup/restore, body limits and workload tests are required. This increment is intended for loopback-only development.
