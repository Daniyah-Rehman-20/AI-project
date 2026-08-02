# Live Demo (Cloudflare Tunnel)

Ephemeral public URLs (valid while the agent/tunnels are running):

| Service | URL |
|---------|-----|
| **Frontend** | https://blvd-common-fought-bloomberg.trycloudflare.com |
| **API / Swagger** | https://stakeholders-moon-cambridge-addressing.trycloudflare.com/docs |
| **Health** | https://stakeholders-moon-cambridge-addressing.trycloudflare.com/api/v1/health |

## Login

- **Email:** `admin@example.com`
- **Password:** `ChangeMeAdmin123!`

## Local (this VM)

```bash
# Backend
cd backend && source .venv/bin/activate && set -a && source .env && set +a
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm run dev -- -H 0.0.0.0 -p 3000
```

## Full stack with Docker

```bash
cp .env.example .env
docker compose up --build
```
