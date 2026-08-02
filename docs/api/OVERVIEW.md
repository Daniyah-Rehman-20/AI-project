# API Overview

Interactive OpenAPI (Swagger): `/docs`  
ReDoc: `/redoc`  
OpenAPI JSON: `/openapi.json`

## Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/oauth/google`

## Core

- Incidents: `/api/v1/incidents`
- Logs: `/api/v1/logs`
- Documents: `/api/v1/documents`
- Search (RAG): `/api/v1/search`
- Reports: `/api/v1/reports`
- Analytics: `/api/v1/analytics/dashboard`, `/api/v1/analytics/ai-usage`
- Notifications, Feedback, Audit, API Keys, Prompts, Integrations, Health
