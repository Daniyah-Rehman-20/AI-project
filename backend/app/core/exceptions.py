"""Application exception hierarchy."""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base application exception with HTTP mapping metadata."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | list[Any] | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        resolved_code = code or error_code
        if resolved_code is not None:
            self.error_code = resolved_code

    @property
    def code(self) -> str:
        return self.error_code


class ValidationError(AppException):
    status_code = 422
    error_code = "validation_error"


class AuthenticationError(AppException):
    status_code = 401
    error_code = "authentication_error"


class UnauthorizedError(AuthenticationError):
    """Backward-compatible alias for authentication failures."""

    error_code = "unauthorized"


class AuthorizationError(AppException):
    status_code = 403
    error_code = "authorization_error"


class ForbiddenError(AuthorizationError):
    """Backward-compatible alias."""

    error_code = "forbidden"


class NotFoundError(AppException):
    status_code = 404
    error_code = "not_found"


class ConflictError(AppException):
    status_code = 409
    error_code = "conflict"


class RateLimitError(AppException):
    status_code = 429
    error_code = "rate_limit_exceeded"


class ExternalServiceError(AppException):
    status_code = 502
    error_code = "external_service_error"


class ServiceUnavailableError(AppException):
    status_code = 503
    error_code = "service_unavailable"


class DatabaseError(AppException):
    status_code = 500
    error_code = "database_error"


class StorageError(AppException):
    status_code = 500
    error_code = "storage_error"


class KafkaError(AppException):
    status_code = 500
    error_code = "kafka_error"


class VectorStoreError(AppException):
    status_code = 500
    error_code = "vector_store_error"


class LLMError(AppException):
    status_code = 500
    error_code = "llm_error"
