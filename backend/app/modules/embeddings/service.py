"""LLM and embedding model factories with graceful fallbacks."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FallbackChatModel(BaseChatModel):
    """Deterministic offline chat model for CI/dev without API keys."""

    model_name: str = "fallback-deterministic"

    @property
    def _llm_type(self) -> str:
        return "fallback-deterministic"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        user_content = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                user_content = str(msg.content)
                break

        response = self._build_response(user_content)
        generation = ChatGeneration(message=AIMessage(content=response))
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _build_response(self, prompt: str) -> str:
        if "classify" in prompt.lower():
            return json.dumps(
                {
                    "category": "infrastructure",
                    "confidence": 0.75,
                    "summary": "Automated classification based on incident signals.",
                }
            )
        if "root cause" in prompt.lower() or "root_cause" in prompt.lower():
            return json.dumps(
                {
                    "root_cause": "Service dependency timeout under elevated load.",
                    "confidence": 0.7,
                    "evidence": ["Elevated error rates", "Timeout patterns in logs"],
                }
            )
        if "recommend" in prompt.lower():
            return json.dumps(
                {
                    "recommendations": [
                        "Increase connection pool size",
                        "Add circuit breaker for downstream service",
                        "Review recent deployments",
                    ],
                }
            )
        if "report" in prompt.lower() or "postmortem" in prompt.lower():
            return (
                "## Incident Postmortem\n\n"
                "### Summary\n"
                "Automated analysis identified a service degradation event.\n\n"
                "### Root Cause\n"
                "Dependency timeout under load.\n\n"
                "### Action Items\n"
                "- Scale connection pools\n"
                "- Add monitoring alerts\n"
            )
        digest = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        return json.dumps(
            {
                "response": f"Fallback analysis complete (ref: {digest})",
                "note": "Configure LLM_PROVIDER and API keys for production responses.",
            }
        )


class HashEmbeddingFallback(Embeddings):
    """Deterministic hash-based embeddings for offline/CI environments."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = text.lower().split()
        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % self.dimension
            vector[idx] += 1.0 / (i + 1)
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    try:
        if provider == "gemini" and settings.gemini_api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.2,
            )

        if provider == "openai" and settings.openai_api_key:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=0.2,
            )

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.2,
            )
    except Exception as exc:
        logger.warning("llm_provider_init_failed", provider=provider, error=str(exc))

    logger.info("using_fallback_chat_model", provider=provider)
    return FallbackChatModel()


def get_embedding_model(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower()

    try:
        if provider in ("sentence-transformers", "huggingface", "hf"):
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
    except Exception as exc:
        logger.warning(
            "embedding_provider_init_failed",
            provider=provider,
            error=str(exc),
        )

    logger.info("using_hash_embedding_fallback", dimension=settings.embedding_dimension)
    return HashEmbeddingFallback(dimension=settings.embedding_dimension)
