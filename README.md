<div align="center">
  <img src="frontend/public/brand/forgemind-mark.svg" width="96" alt="ForgeMind AI logo" />
  <h1>ForgeMind AI</h1>
  <p><strong>An agentic factory copilot for predictive maintenance, visual quality control, production intelligence, and industrial operations.</strong></p>

  <p>
    <a href="https://github.com/MohamadKtich/forgemind-ai/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/MohamadKtich/forgemind-ai/ci.yml?branch=main&label=CI"></a>
    <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB">
    <img alt="Node" src="https://img.shields.io/badge/Node.js-22%2B-339933">
    <img alt="License" src="https://img.shields.io/badge/License-MIT-2ea44f">
    <img alt="Languages" src="https://img.shields.io/badge/UI-English%20%7C%20Arabic-24c7e8">
  </p>

  <p>
    <a href="README_AR.md">العربية</a> ·
    <a href="docs/ARCHITECTURE.md">Architecture</a> ·
    <a href="docs/API.md">API</a> ·
    <a href="docs/SUPABASE_SETUP.md">Supabase</a> ·
    <a href="docs/REAL_AI_MODELS.md">AI models</a>
  </p>
</div>

![ForgeMind AI social preview](assets/github-social-preview.png)

## Overview

ForgeMind AI is a full-stack, local-first industrial intelligence platform. It connects machine telemetry, predictive-maintenance analysis, visual product inspection, production monitoring, work orders, alerts, reports, a bilingual factory assistant, and a digital twin in one operational workflow.

It is intentionally built as a real application rather than a collection of disconnected mock dashboards:

```text
Machine or simulator signal
          ↓
FastAPI validation and persistence
          ↓
AI / anomaly / vision analysis
          ↓
Risk, defect, or production decision
          ↓
Alert, recommendation, report, and operator action
```

![System architecture](docs/images/architecture.svg)

## Core capabilities

| Area | What is implemented |
|---|---|
| Predictive maintenance | Health score, failure probability, anomaly score, RUL estimate, risk ranking, likely issue, contributing factors, and maintenance recommendation |
| Visual quality control | Image validation, surface anomaly analysis, golden-reference comparison, defect classification, region localization, annotated outputs, and inspection history |
| Factory operations | Multi-factory and machine management, sensor history, production records, OEE, downtime, rejects, maintenance work orders, and audit logs |
| Agentic assistant | Arabic/English operational answers grounded in current machines, predictions, alerts, maintenance, production, and quality records |
| Digital twin | Live sensor simulation, degradation, failure scenarios, quality events, production events, and automatic alert generation |
| Reports | Executive, maintenance, quality, production, machine-health, and incident PDF reports plus CSV export |
| Hardware-ready layer | Secured sensor-ingestion API and recorded commands for machines, conveyors, warning lights, inspections, and product rejection |
| Experience | Responsive Next.js interface, role-based access, Arabic RTL, English LTR, dark/light/system themes, loading/error/empty states |

## Real application screenshot

<img src="docs/images/quality-control-real.png" alt="ForgeMind AI visual quality control page" width="100%" />

## Technology stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, Recharts, Lucide Icons
**Backend:** FastAPI, Python, Pydantic, SQLAlchemy, SQLite/PostgreSQL
**AI and vision:** Scikit-learn, Isolation Forest, OpenCV, Joblib, NumPy, Pandas
**Reports and operations:** ReportLab, CSV, Docker Compose, GitHub Actions

## AI model transparency

ForgeMind AI exposes an in-product model registry through the **AI Models** page and `GET /api/models/status`.

- The bundled general predictive-maintenance model is a working fallback trained on generated benchmark-style industrial data.
- A complete MetroPT-3 training pipeline is included for compressor/APU anomaly and failure-risk experiments.
- A complete KSDD training pipeline is included for industrial surface-defect classification and localization experiments.
- **Real-data model weights are not bundled in this repository.** The application labels fallback and trained model states explicitly.
- No model should control physical equipment without target-factory validation, threshold calibration, cybersecurity review, human approval, and industrial safety controls.

See [Real AI Models](docs/REAL_AI_MODELS.md) and [Third-Party Dataset Notice](THIRD_PARTY_DATASETS.md).

## Repository structure

```text
forgemind-ai/
├── frontend/                 Next.js application
├── backend/                  FastAPI, SQLAlchemy, AI, vision, reports
│   ├── app/                  APIs, auth, models, services, simulator
│   ├── ml/                   bundled fallback and training pipelines
│   ├── tests/                backend integration tests
│   └── storage/              generated at runtime
├── assets/                   samples and GitHub preview
├── docs/                     architecture, API, setup, models, hardware
├── scripts/                  backup, migration, verification helpers
├── supabase/                 optional PostgreSQL schema
├── docker-compose.yml
└── .github/                  CI and contribution templates
```

## Quick start on Windows

### Requirements

- Python 3.11 or newer
- Node.js 22 or newer
- Approximately 2 GB for installed dependencies

### Automated setup

1. Clone or download the repository.
2. Run `SETUP_WINDOWS.bat` once.
3. Run `START_FORGEMIND.bat`.
4. Open `http://localhost:3000`.

### Manual setup

Backend:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m fastapi dev app/main.py --host 127.0.0.1 --port 8000
```

Frontend in a second terminal:

```bat
cd frontend
npm ci
copy .env.example .env.local
npm run dev
```

URLs:

- Application: `http://localhost:3000`
- Swagger API: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`

## Initial local accounts

These accounts are generated only when `SEED_DEFAULT_USERS=true` and the users table is empty.

| Role | Email | Initial password |
|---|---|---|
| Administrator | `admin@forgemind.ai` | `ForgeMind#2026` |
| Factory Manager | `manager@forgemind.ai` | `ForgeMind#2026` |
| Maintenance Engineer | `maintenance@forgemind.ai` | `ForgeMind#2026` |
| Quality Engineer | `quality@forgemind.ai` | `ForgeMind#2026` |

Change all initial passwords and example keys before any shared or public deployment.

## Supabase PostgreSQL

The backend supports SQLite for local use and PostgreSQL/Supabase for cloud persistence. Install dependencies, copy `backend/.env.example`, and set a private Session Pooler URL:

```env
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

The connection string belongs only in the backend or deployment secret store. Read [Supabase Setup](docs/SUPABASE_SETUP.md) before migrating.

## Verification

```bash
cd backend
pytest -q
python -m compileall app ml

cd ../frontend
npm ci
npm run typecheck
npm run build

cd ..
python scripts/preflight_release.py
```

The release source was backend-tested with **9 passing tests**. GitHub Actions repeats backend tests, TypeScript checking, and the Next.js production build on pushes and pull requests.

## Docker

```bash
docker compose up --build
```

Copy environment examples and replace default secrets before using Docker outside a local development machine.

## Current boundaries

The application is complete as a controlled local software platform and cloud-ready codebase. The following require external infrastructure or factory access:

- Supabase Storage and managed identity integration
- public deployment, domain, HTTPS, monitoring, and backups
- PLC, MQTT, OPC UA, or Modbus gateway connection
- physical conveyor or robotic rejection mechanism
- final model training and validation on the target factory's real data and camera setup
- industrial safety approval for commands affecting equipment

## Author and ownership

**Designed and developed by [Mohamad Abdullatif Ktich](https://www.linkedin.com/in/mohamad-ktich)**

- LinkedIn: [linkedin.com/in/mohamad-ktich](https://www.linkedin.com/in/mohamad-ktich)
- GitHub: [github.com/MohamadKtich](https://github.com/MohamadKtich)
- Email: [ktichmohamad@gmail.com](mailto:ktichmohamad@gmail.com)

## License

Copyright © 2026 Mohamad Abdullatif Ktich. Released under the [MIT License](LICENSE).
