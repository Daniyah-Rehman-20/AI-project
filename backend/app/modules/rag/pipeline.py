"""RAG pipeline: document processing, embedding, and grounded search."""

from __future__ import annotations

import io
import re
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentStatus
from app.core.logging import get_logger
from app.core.storage import get_storage
from app.database.models import Document, DocumentChunk, EmbeddingMetadata
from app.modules.embeddings.service import get_chat_model, get_embedding_model
from app.modules.vectorstore.service import get_vector_store

logger = get_logger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class RAGPipeline:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.storage = get_storage()
        self.vectorstore = get_vector_store()
        self.embeddings = get_embedding_model()
        self.chat_model = get_chat_model()

    def _chunk_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + CHUNK_SIZE, text_len)
            if end < text_len:
                boundary = text.rfind("\n", start, end)
                if boundary > start + CHUNK_SIZE // 2:
                    end = boundary + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - CHUNK_OVERLAP if end < text_len else text_len

        return chunks

    async def _parse_document(self, content: bytes, content_type: str) -> str:
        if content_type == "text/plain" or content_type == "text/markdown":
            return content.decode("utf-8", errors="replace")

        if content_type == "application/pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(content))
                pages = [page.extract_text() or "" for page in reader.pages]
                return "\n\n".join(pages)
            except Exception as exc:
                logger.warning("pdf_parse_failed", error=str(exc))
                return content.decode("utf-8", errors="replace")

        if content_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            try:
                from docx import Document as DocxDocument

                doc = DocxDocument(io.BytesIO(content))
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except Exception as exc:
                logger.warning("docx_parse_failed", error=str(exc))
                return content.decode("utf-8", errors="replace")

        return content.decode("utf-8", errors="replace")

    async def process_document(self, document_id: str) -> dict[str, Any]:
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.PROCESSING.value
        await self.db.flush()

        try:
            content = await self.storage.get_object(document.storage_key)
            text = await self._parse_document(content, document.content_type)
            text = re.sub(r"\s+", " ", text).strip()

            chunks = self._chunk_text(text)
            if not chunks:
                document.status = DocumentStatus.FAILED.value
                await self.db.commit()
                return {"document_id": str(document_id), "chunks": 0, "status": "failed"}

            await self.vectorstore.delete_by_document(str(document_id))

            vectors = self.embeddings.embed_documents(chunks)
            payloads = []
            chunk_records: list[DocumentChunk] = []

            for idx, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    content=chunk_text,
                )
                chunk_records.append(chunk)
                payloads.append(
                    {
                        "document_id": str(document.id),
                        "chunk_id": "",
                        "chunk_index": idx,
                        "content": chunk_text,
                        "title": document.title,
                    }
                )

            self.db.add_all(chunk_records)
            await self.db.flush()

            for idx, chunk in enumerate(chunk_records):
                payloads[idx]["chunk_id"] = str(chunk.id)

            vector_ids = await self.vectorstore.upsert(
                vectors=vectors,
                payloads=payloads,
            )

            for chunk, vector_id in zip(chunk_records, vector_ids, strict=True):
                meta = EmbeddingMetadata(
                    chunk_id=chunk.id,
                    vector_id=vector_id,
                )
                self.db.add(meta)

            document.status = DocumentStatus.INDEXED.value
            await self.db.commit()
            logger.info(
                "document_processed",
                document_id=str(document_id),
                chunks=len(chunks),
            )
            return {
                "document_id": str(document_id),
                "chunks": len(chunks),
                "status": "indexed",
            }

        except Exception as exc:
            document.status = DocumentStatus.FAILED
            await self.db.commit()
            logger.error("document_processing_failed", document_id=str(document_id), error=str(exc))
            raise

    async def search(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        query_vector = self.embeddings.embed_query(query)
        results = await self.vectorstore.search(query_vector, top_k=top_k)

        citations: list[dict[str, Any]] = []
        context_parts: list[str] = []

        for hit in results:
            payload = hit.get("payload", {})
            content = payload.get("content", "")
            citations.append(
                {
                    "document_id": payload.get("document_id", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "content": content[:500],
                    "score": hit.get("score", 0.0),
                }
            )
            context_parts.append(content)

        context = "\n\n---\n\n".join(context_parts[:top_k])

        if not context:
            return {
                "answer": "No relevant documents found in the knowledge base.",
                "citations": [],
            }

        messages = [
            SystemMessage(
                content=(
                    "You are an incident intelligence assistant. Answer based ONLY on "
                    "the provided context. If the context is insufficient, say so. "
                    "Cite specific details from the context."
                )
            ),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
        ]

        try:
            response = await self.chat_model.ainvoke(messages)
            answer = str(response.content)
        except Exception as exc:
            logger.warning("rag_llm_failed", error=str(exc))
            answer = (
                f"Found {len(citations)} relevant document sections. "
                f"Top match (score {citations[0]['score']:.2f}): "
                f"{citations[0]['content'][:200]}..."
            )

        return {"answer": answer, "citations": citations}
