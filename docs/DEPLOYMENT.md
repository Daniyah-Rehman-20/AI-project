# Deployment Guide

## Docker Compose (recommended for demo / staging)

```bash
cp .env.example .env
# Set production secrets, LLM keys, APP_ENV=production, APP_DEBUG=false
docker compose up -d --build
docker compose --profile with-proxy up -d nginx
```

## Production checklist

1. Set strong `APP_SECRET_KEY` and `JWT_SECRET_KEY` (≥32 random bytes).
2. Use PostgreSQL: enable `--profile postgres` and set `DATABASE_URL`.
3. Run `alembic upgrade head` before serving traffic.
4. Put TLS termination in front of nginx (or a cloud LB).
5. Restrict CORS to your frontend origin.
6. Configure Kafka retention and Qdrant persistence volumes.
7. Enable LangSmith / OTEL for observability.
8. Rotate seed admin password immediately.
9. Store MinIO/S3 credentials in a secrets manager.
10. Set resource limits on worker containers (LLM + embeddings are CPU-heavy).

## Kubernetes sketch

Deploy each Compose service as a Deployment + Service; use StatefulSets for Kafka/Zookeeper/Postgres/Qdrant; ConfigMaps for non-secret config; Secrets for keys. Horizontal-scale `worker` replicas on the same consumer group.

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
