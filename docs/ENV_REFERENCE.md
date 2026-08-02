# Environment Variable Reference

See `.env.example` for the full list. Critical variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_SECRET_KEY` | App secret (≥16 chars) | required |
| `JWT_SECRET_KEY` | JWT signing key | required |
| `DATABASE_URL` | Async SQLAlchemy URL | SQLite file |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `localhost:9092` |
| `QDRANT_URL` | Vector DB | `http://localhost:6333` |
| `S3_ENDPOINT` | MinIO/S3 | `http://localhost:9000` |
| `LLM_PROVIDER` | `gemini` \| `openai` \| `ollama` | `gemini` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | LLM credentials | empty (fallback mode) |
| `EMBEDDING_MODEL` | HF model id | `BAAI/bge-small-en-v1.5` |
| `SEED_ADMIN_EMAIL` | Bootstrapped admin | `admin@incident-intel.dev` |
| `GOOGLE_CLIENT_ID/SECRET` | OAuth | empty |
| `SLACK_WEBHOOK_URL` | Notifications | empty |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | API throttle | `60` |
