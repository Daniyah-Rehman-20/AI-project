"""Notifications module."""

from app.modules.notifications.router import router
from app.modules.notifications.service import NotificationService

__all__ = ["router", "NotificationService"]
