"""Embeddings module."""

from app.modules.embeddings.service import (
    FallbackChatModel,
    HashEmbeddingFallback,
    get_chat_model,
    get_embedding_model,
)

__all__ = [
    "FallbackChatModel",
    "HashEmbeddingFallback",
    "get_chat_model",
    "get_embedding_model",
]
