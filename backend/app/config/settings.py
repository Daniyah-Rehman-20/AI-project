"""Pydantic settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Incident Intelligence Platform", alias="APP_NAME")
    app_env: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_secret_key: str = Field(min_length=16, alias="APP_SECRET_KEY")
    app_api_prefix: str = Field(default="/api/v1", alias="APP_API_PREFIX")
    app_frontend_url: str = Field(default="http://localhost:3000", alias="APP_FRONTEND_URL")
    app_backend_url: str = Field(default="http://localhost:8000", alias="APP_BACKEND_URL")
    app_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="APP_CORS_ORIGINS",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/incident_intel.db",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL")

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_consumer_group: str = Field(
        default="incident-intel-workers",
        alias="KAFKA_CONSUMER_GROUP",
    )
    kafka_auto_offset_reset: Literal["earliest", "latest"] = Field(
        default="earliest",
        alias="KAFKA_AUTO_OFFSET_RESET",
    )

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="incident_knowledge", alias="QDRANT_COLLECTION")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    # Object storage (MinIO / S3)
    s3_endpoint: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="incident-docs", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL")

    # JWT
    jwt_secret_key: str = Field(min_length=16, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # OAuth — Google
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/oauth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    # LLM providers
    llm_provider: Literal["gemini", "openai", "ollama"] = Field(
        default="gemini", alias="LLM_PROVIDER"
    )
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # Embeddings
    embedding_provider: str = Field(default="sentence-transformers", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    # LangSmith
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="incident-intelligence", alias="LANGCHAIN_PROJECT")

    # OpenTelemetry
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(default="incident-intel-api", alias="OTEL_SERVICE_NAME")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, alias="RATE_LIMIT_REQUESTS_PER_MINUTE")

    # External integrations
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_webhook_secret: str | None = Field(default=None, alias="GITHUB_WEBHOOK_SECRET")
    jira_base_url: str | None = Field(default=None, alias="JIRA_BASE_URL")
    jira_email: str | None = Field(default=None, alias="JIRA_EMAIL")
    jira_api_token: str | None = Field(default=None, alias="JIRA_API_TOKEN")
    slack_bot_token: str | None = Field(default=None, alias="SLACK_BOT_TOKEN")
    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    gmail_client_id: str | None = Field(default=None, alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str | None = Field(default=None, alias="GMAIL_CLIENT_SECRET")
    prometheus_url: str = Field(default="http://prometheus:9090", alias="PROMETHEUS_URL")
    grafana_url: str = Field(default="http://grafana:3000", alias="GRAFANA_URL")
    grafana_api_key: str | None = Field(default=None, alias="GRAFANA_API_KEY")

    # Worker
    worker_concurrency: int = Field(default=4, alias="WORKER_CONCURRENCY")
    worker_poll_interval_ms: int = Field(default=500, alias="WORKER_POLL_INTERVAL_MS")

    # Seed admin
    seed_admin_email: str = Field(default="admin@example.com", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="ChangeMeAdmin123!", alias="SEED_ADMIN_PASSWORD")
    seed_admin_name: str = Field(default="Platform Admin", alias="SEED_ADMIN_NAME")

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str]) -> str:
        if isinstance(value, list):
            return ",".join(value)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def kafka_brokers(self) -> list[str]:
        return [
            broker.strip() for broker in self.kafka_bootstrap_servers.split(",") if broker.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
