# Enterprise AI Incident Intelligence Platform

**AetherOps / IncidentIQ** — production-grade, event-driven platform that automatically ingests logs, deployment events, tickets, and documents; then uses **LangGraph multi-agent workflows** and **RAG** to triage incidents, identify root causes, recommend fixes, and generate postmortems.

> This is **not** a chatbot. AI is a backend capability that powers asynchronous incident-intelligence workflows.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Next.js UI │────▶│  FastAPI API │────▶│  SQLite / PostgreSQL        │
│  (App Router)│     │  + JWT/RBAC  │     │  Redis cache                │
└─────────────┘     └──────┬───────┘     │  MinIO (S3) object store    │
                           │             └─────────────────────────────┘
                           ▼
                    ┌──────────────┐
                    │ Apache Kafka │  topics: incident-created,
                    └──────┬───────┘  documents-uploaded, …
                           ▼
                    ┌──────────────────────────────────────┐
                    │ Workers (LangGraph Agents + RAG)     │
                    │ Classifier → RCA → Retrieve → Fix →  │
                    │ Report → Notify                      │
                    └──────────────┬───────────────────────┘
                                   ▼
                           ┌──────────────┐
                           │ Qdrant       │
                           │ Embeddings   │
                           └──────────────┘
```

**Clean Architecture layers:** Presentation → API → Application (services) → Domain → Infrastructure (DB, Kafka, Redis, Qdrant, S3).

**Patterns:** Repository + Service, Dependency Injection, SOLID, RBAC.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind, TanStack Query, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic |
| Auth | JWT + refresh rotation, Google OAuth, API keys |
| DB | SQLite (dev) / PostgreSQL (prod) via same ORM |
| Cache | Redis |
| Messaging | Apache Kafka |
| Vector DB | Qdrant |
| LLM | Gemini / OpenAI / Ollama (configurable) |
| AI | LangGraph agents + LangChain RAG |
| Embeddings | BAAI/bge-small-en-v1.5 (sentence-transformers) |
| Storage | MinIO / S3 |
| Observability | structlog, Prometheus metrics, optional LangSmith / OTEL |
| CI/CD | GitHub Actions |
| Containers | Docker Compose |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose **or**
- Python 3.12+, Node 20+, Redis (optional for local API-only)

### One-command full stack

```bash
cp .env.example .env
# Edit .env — set GEMINI_API_KEY or OPENAI_API_KEY (optional; offline fallback works)
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| Qdrant | http://localhost:6333 |
| Kafka | localhost:9092 |

**Default admin:** `admin@incident-intel.dev` / `ChangeMeAdmin123!`

### Local development (API only)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
cp ../.env.example ../.env
export $(grep -v '^#' ../.env | xargs)
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Run workers (Kafka consumers)

```bash
cd backend
python -m app.workers.main
```

---

## Database Schema

Core tables: `users`, `roles`, `sessions`, `api_keys`, `incidents`, `logs`, `documents`, `chunks`, `embedding_metadata`, `reports`, `notifications`, `audit_logs`, `feedback`, `analytics_events`, `prompt_versions`, `model_usage`.

Swap to PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/incident_intel
```

```bash
docker compose --profile postgres up -d postgres
cd backend && alembic upgrade head
```

---

## AI Agents (LangGraph)

1. **Incident Classifier** — severity + category  
2. **Root Cause Analyzer** — log/description RCA  
3. **Retrieval Agent** — similar knowledge from Qdrant  
4. **Fix Recommendation Agent** — remediation steps  
5. **Report Generator** — Markdown postmortem  
6. **Notification Agent** — Slack/email summary  

Pipeline is **async via Kafka** (`incident-created` → worker → `analysis-completed` / `reports-generated` / `notifications`).

---

## RAG Pipeline

Upload → Chunk (LangChain splitter) → Embed (bge-small) → Qdrant → Retrieve → LLM grounded answer **with citations**.

---

## REST API (Swagger)

Interactive docs: **http://localhost:8000/docs**

Key groups: Auth, Users, Incidents, Logs, Documents, Search, Reports, Notifications, Analytics, Feedback, Audit, API Keys, Prompts, Integrations, Health.

---

## Testing

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

```bash
cd frontend
npm run build
```

CI runs lint, tests, coverage, and Docker image builds on every push/PR.

---

## Security

- JWT access + rotating refresh tokens  
- Password hashing (bcrypt)  
- RBAC permission matrix (`admin`, `analyst`, `engineer`, `viewer`)  
- API keys (hashed at rest)  
- Rate limiting (Redis / in-memory fallback)  
- CORS, input validation (Pydantic), SQLAlchemy parameterization  
- Prompt-injection sanitization for LLM inputs  
- Secrets via environment variables only  

---

## Project Structure

```
backend/app/
  config/          # Settings
  core/            # Security, enums, cache, kafka, storage, repository
  database/        # Models, session, seed
  dependencies/    # DI + RBAC
  middleware/      # Request ID, rate limit
  modules/         # Domain modules (auth, incidents, rag, agents, …)
  workers/         # Kafka consumers
frontend/          # Next.js App Router UI
infra/nginx/       # Reverse proxy
docs/              # Architecture & diagrams
.github/workflows/ # CI/CD
```

---

## Documentation

- [Architecture](docs/architecture/ARCHITECTURE.md)
- [ER Diagram](docs/diagrams/ER.md)
- [Sequence Diagrams](docs/diagrams/SEQUENCES.md)
- [Environment Reference](docs/ENV_REFERENCE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing](docs/CONTRIBUTING.md)

---

## License

MIT — built as a FAANG-level portfolio demonstration of enterprise AI systems engineering.
