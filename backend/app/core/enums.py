"""Domain enumerations and RBAC permission matrix."""

from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class IncidentSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Backward-compatible alias used by service/repository layers.
Severity = IncidentSeverity


class IncidentStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCategory(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    THIRD_PARTY = "third_party"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class AuditAction(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    INCIDENT_ANALYZE = "incident_analyze"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_INDEX = "document_index"
    REPORT_GENERATE = "report_generate"
    SEARCH = "search"
    EXPORT = "export"
    ADMIN_ACTION = "admin_action"


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    WARN = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        "users:read",
        "users:write",
        "incidents:read",
        "incidents:write",
        "incidents:analyze",
        "logs:read",
        "logs:write",
        "documents:read",
        "documents:write",
        "search:read",
        "reports:read",
        "reports:write",
        "notifications:read",
        "notifications:write",
        "analytics:read",
        "feedback:read",
        "feedback:write",
        "audit:read",
        "api_keys:read",
        "api_keys:write",
        "prompts:read",
        "prompts:write",
        "integrations:read",
        "integrations:write",
        "admin:all",
    }
)

RBAC_PERMISSIONS: dict[RoleName, frozenset[str]] = {
    RoleName.ADMIN: frozenset({"admin:all"}),
    RoleName.ANALYST: frozenset(
        {
            "incidents:read",
            "incidents:write",
            "incidents:analyze",
            "logs:read",
            "logs:write",
            "documents:read",
            "documents:write",
            "search:read",
            "reports:read",
            "reports:write",
            "notifications:read",
            "notifications:write",
            "analytics:read",
            "feedback:read",
            "feedback:write",
            "audit:read",
            "prompts:read",
            "integrations:read",
        }
    ),
    RoleName.ENGINEER: frozenset(
        {
            "incidents:read",
            "incidents:write",
            "logs:read",
            "logs:write",
            "documents:read",
            "documents:write",
            "search:read",
            "reports:read",
            "notifications:read",
            "feedback:write",
        }
    ),
    RoleName.VIEWER: frozenset(
        {
            "incidents:read",
            "logs:read",
            "documents:read",
            "search:read",
            "reports:read",
            "notifications:read",
            "analytics:read",
        }
    ),
}


def role_has_permission(
    role_name: str, permission: str, extra_permissions: list[str] | None = None
) -> bool:
    """Return True if the role (plus optional extra grants) includes the permission."""
    try:
        role = RoleName(role_name)
    except ValueError:
        return False

    grants = set(RBAC_PERMISSIONS.get(role, frozenset()))
    if extra_permissions:
        grants.update(extra_permissions)

    if "admin:all" in grants:
        return True
    return permission in grants


def expand_role_permissions(role_name: str, extra_permissions: list[str] | None = None) -> set[str]:
    """Expand a role into its effective permission set."""
    try:
        role = RoleName(role_name)
    except ValueError:
        return set(extra_permissions or [])

    grants = set(RBAC_PERMISSIONS.get(role, frozenset()))
    if extra_permissions:
        grants.update(extra_permissions)

    if "admin:all" in grants:
        return set(ALL_PERMISSIONS)
    return grants
