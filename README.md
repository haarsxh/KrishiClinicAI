# KrishiClinic AI

AI-Powered Crop Disease Detection and Regional Outbreak Surveillance Platform.
Developed for Manipal University Jaipur Hackathon — Theme: AgriTech (PS #1: AI Crop Disease Detection).

## Problem Statement & Objective

In modern agriculture, detecting crop diseases at an early stage is critical to preventing devastating harvest losses. KrishiClinic AI provides smallholder and commercial farmers with an intelligent diagnostic companion that:
1. Identifies crop diseases from ordinary field smartphone photographs.
2. Estimates infection progression and severity (Early, Moderate, Severe).
3. Provides safe, locally sourced organic and chemical treatment advisories with exact dosages.
4. Detects ambiguous samples and routes low-confidence predictions to accredited agronomists.
5. Functions offline with local deep learning models (EfficientNetV2-S).
6. Delivers findings in local languages (Hindi, Telugu, Marathi, Spanish, English) with voice speech readout.
7. Features a regional outbreak radar that aggregates anonymized detections to warn neighboring farmers within a 25km perimeter.

## Architecture

```
+----------------------------------------------------------------+
|                         KrishiClinic AI                        |
+----------------------------------------------------------------+
|  Frontend (Next.js 14 App Router, TypeScript, Responsive CSS)  |
+----------------------------------------------------------------+
                               |
                               v
+----------------------------------------------------------------+
|         Backend API (FastAPI, Python 3.12, Async SQLAlchemy)   |
+----------------------------------------------------------------+
        |                      |                      |
        v                      v                      v
+---------------+      +---------------+      +---------------+
| PostgreSQL DB |      | AI Engine     |      | Outbreak Radar|
| & Migrations  |      | Multi-Model   |      | Surveillance  |
+---------------+      +---------------+      +---------------+
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
     +--------------+   +--------------+   +--------------+
     | Google Gemini|   | Groq LLaMA-4 |   | Local PyTorch|
     | Vision API   |   | Vision API   |   | Offline Net  |
     +--------------+   +--------------+   +--------------+
```

## Technology Stack

- Frontend: Next.js 14, React 18, TypeScript, Recharts, Web Speech API
- Backend: FastAPI, Python 3.12, Pydantic V2, SQLAlchemy 2.0, AsyncPG / aiosqlite
- Database: PostgreSQL 15 / SQLite with Alembic migrations
- AI Inference: Google Gemini, Groq, OpenAI, Local PyTorch (EfficientNetV2-S), Mock Engine
- Storage: Local Storage Abstraction
- Deployment: Vercel (Frontend), Render / Docker (Backend)

## Features & Implementation

### 1. Image-Based Disease Diagnosis
Accepts field photographs under varied lighting conditions. Analyzes leaf symptoms across major crops including Tomato, Potato, Wheat, Rice, Cotton, Soybean, and Corn.

### 2. Severity Assessment
Classifies damage stages into Low, Medium, and High infestation levels to guide timely containment before disease spreads across entire acres.

### 3. Actionable Treatment Advisories
Delivers dual-track intervention plans:
- Immediate chemical fungicides/bactericides with precise volumetric dilution guidance.
- Preventive cultural and organic practices (e.g. neem oil, copper sprays, soil drainage).

### 4. Confidence-Based Auto-Release & Low-Confidence Referral Workflow
High-confidence predictions (confidence >= 0.70, configurable via `AUTO_APPROVE_CONFIDENCE_THRESHOLD`) are automatically released as `REVIEWED` and visible to farmers immediately. When model confidence falls below 70%, predictions remain gated as `PENDING_REVIEW` with masked advisory details, routed to accredited Agronomists and Admins for manual verification.

### 5. Offline Model Execution & Zero-Network Capability
Backend model weights (EfficientNetV2-S) are prefetched and bundled directly at Docker build time in `backend/app/ai/weights`. When running `AI_PROVIDER=local`, disease inference and dictionary-based advisory translations operate with zero network access required after build.
*(Note: Full frontend Progressive Web App (PWA) and offline-sync queue are planned roadmap stretch goals).*

### 6. Voice Readout & Regional Languages
Farmers can toggle between English, Hindi, Telugu, Marathi, and Spanish. A dedicated speech synthesis player reads the full advisory out loud.

### 7. Regional Outbreak Surveillance Radar (Bonus)
Aggregates anonymized diagnosis reports into localized disease clusters. Displays active cases, threat levels, and perimeter advisories to warn neighboring farms before spores reach their fields.

### 8. Treatment Recovery Tracker
Allows farmers to upload post-treatment follow-up photos alongside recovery notes to monitor plant recuperation over time.

## Quick Start

### Prerequisites
- Python 3.12 (3.10+ works, 3.12 is what CI and Docker use)
- Node.js 18+
- Git
- Docker + Docker Compose (optional — only for the containerised setup)

### Option A — Docker Compose (everything at once)

```bash
cp .env.example .env          # then set JWT_SECRET to any long random string
docker compose up --build
```

This starts PostgreSQL, the API on http://localhost:8000, and the dashboard on
http://localhost:3000. Nothing else is required — `AI_PROVIDER` defaults to `mock`,
so no AI API keys are needed to run or demo the project.

### Option B — Run locally without Docker

**1. Configure environment**

`JWT_SECRET` is mandatory: the API refuses to start without it. The quickest
zero-dependency setup uses SQLite, so you don't need a PostgreSQL server:

```bash
cp .env.example .env
```

Then edit `.env` so it contains at least:

```bash
JWT_SECRET=replace-with-a-long-random-string   # e.g. python3 -c "import secrets;print(secrets.token_urlsafe(32))"
DATABASE_URL=sqlite+aiosqlite:///./krishiclinic.db
AI_PROVIDER=mock
```

> To use PostgreSQL instead, set
> `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/krishiclinic`
> and make sure a server is running (`docker compose up db` will provide one).

**2. Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_db     # create the tables
python -m app.db.seed         # optional: demo users + 25 sample records
uvicorn app.main:app --reload --port 8000
```

> `scripts/init_db.py` picks the right path automatically: it runs the Alembic
> migrations for PostgreSQL, and creates the schema straight from the ORM models
> for SQLite (the migration chain itself is PostgreSQL-specific).

**3. Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

The web dashboard will be available at http://localhost:3000 and the API documentation at http://localhost:8000/docs.

### Demo Accounts

`python -m app.db.seed` (run automatically in Docker) creates three accounts,
all with the password `password123`:

| Username | Role |
| --- | --- |
| `farmer` | FARMER |
| `agronomist` | AGRONOMIST |
| `admin` | ADMIN |

### Using the offline local model (optional)

`AI_PROVIDER=local` runs EfficientNetV2-S on-device and needs `model.pt` +
`metadata.json` in `backend/app/ai/weights/`. These are pulled from a private
Hugging Face repo, so the build only warns (never fails) when they are
unavailable — every other provider keeps working. To bundle them, supply a token
with access:

```bash
docker build --build-arg HF_TOKEN=hf_xxx --build-arg REQUIRE_WEIGHTS=true ./backend
```

Alternatively point `MODEL_REPO_ID` at your own repo, or drop the two files into
`backend/app/ai/weights/` manually.

## API Specification

- GET /health: System health and database connectivity check.
- POST /api/v1/predictions: Upload and diagnose crop image.
- GET /api/v1/predictions: List historical predictions with filters.
- GET /api/v1/predictions/{id}: Retrieve detailed diagnosis and advisory.
- POST /api/v1/predictions/{id}/followup: Upload recovery tracking image.
- GET /api/v1/outbreaks/summary: Fetch active regional disease clusters.
- POST /api/v1/outbreaks/subscribe: Subscribe to proximity SMS warnings.
- GET /api/v1/analytics/summary: Aggregate disease distribution statistics.
- POST /api/v1/translate: Localized translation for advisory text.

## License

MIT License
