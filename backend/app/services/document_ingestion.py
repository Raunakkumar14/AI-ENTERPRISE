from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.document import (
    EMBEDDING_DIMENSIONS,
    Document,
    DocumentChunk,
    DocumentStatus,
)
from app.services.embeddings import EmbeddingProvider, EmbeddingProviderError

logger = logging.getLogger(__name__)


class DocumentParseError(Exception):
    pass


@dataclass(frozen=True)
class ExtractedDocument:
    pages: list[tuple[int | None, str]]
    page_count: int | None


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int | None
    content: str


def extract_document_text(filename: str, content: bytes) -> ExtractedDocument:
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension == "pdf":
        return _extract_pdf(content)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("Text document is not valid UTF-8") from exc
    if not text.strip():
        raise DocumentParseError("Document contains no extractable text")
    _check_text_limit(len(text))
    return ExtractedDocument(pages=[(None, text)], page_count=None)


def _extract_pdf(content: bytes) -> ExtractedDocument:
    if b"%PDF-" not in content[:1024]:
        raise DocumentParseError("Uploaded PDF has an invalid file signature")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        pages: list[tuple[int | None, str]] = []
        total_characters = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            total_characters += len(text)
            _check_text_limit(total_characters)
            if text.strip():
                pages.append((page_number, text))
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("PDF could not be parsed") from exc
    if not pages:
        raise DocumentParseError("PDF contains no extractable text")
    return ExtractedDocument(pages=pages, page_count=len(reader.pages))


def _check_text_limit(character_count: int) -> None:
    if character_count > settings.MAX_EXTRACTED_TEXT_CHARS:
        raise DocumentParseError("Extracted document text exceeds the configured limit")


def split_into_chunks(
    pages: Sequence[tuple[int | None, str]],
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[TextChunk]:
    size = chunk_size if chunk_size is not None else settings.DOCUMENT_CHUNK_SIZE
    overlap_size = overlap if overlap is not None else settings.DOCUMENT_CHUNK_OVERLAP
    if size <= 0 or overlap_size < 0 or overlap_size >= size:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size")

    chunks: list[TextChunk] = []
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        page_number=page_number,
                        content=chunk,
                    )
                )
            if end == len(text):
                break
            start = end - overlap_size
    return chunks


async def process_uploaded_document(
    document_id: int,
    filename: str,
    content: bytes,
    embedding_provider: EmbeddingProvider,
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
) -> None:
    async with session_factory() as session:
        result = await session.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            return
        document.status = DocumentStatus.PROCESSING.value
        document.error_code = None
        document.error_message = None
        await session.commit()

    try:
        extracted = await run_in_threadpool(extract_document_text, filename, content)
        chunks = split_into_chunks(extracted.pages)
        if not chunks:
            raise DocumentParseError("Document contains no extractable text")

        vectors: list[list[float]] = []
        for batch_start in range(0, len(chunks), 64):
            batch = chunks[batch_start : batch_start + 64]
            vectors.extend(await embedding_provider.embed([chunk.content for chunk in batch]))
        if len(vectors) != len(chunks):
            raise EmbeddingProviderError("Embedding provider returned the wrong number of vectors")
        if any(
            not isinstance(vector, (list, tuple))
            or len(vector) != EMBEDDING_DIMENSIONS
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in vector
            )
            for vector in vectors
        ):
            raise EmbeddingProviderError("Embedding provider returned invalid vectors")

        async with session_factory() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            if document is None:
                return
            document.page_count = extracted.page_count
            document.chunk_count = len(chunks)
            document.status = DocumentStatus.COMPLETED.value
            document.error_code = None
            document.error_message = None
            session.add_all(
                [
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        content=chunk.content,
                        embedding=vector,
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ]
            )
            await session.commit()
    except DocumentParseError:
        await _mark_failed(
            document_id,
            "document_parse_failed",
            "The file could not be read as a supported text document.",
            session_factory,
        )
    except EmbeddingProviderError:
        await _mark_failed(
            document_id,
            "embedding_failed",
            "Embeddings could not be generated; verify the configured provider.",
            session_factory,
        )
    except Exception:
        logger.exception("Document ingestion failed for document %s", document_id)
        await _mark_failed(
            document_id,
            "processing_failed",
            "The document could not be processed.",
            session_factory,
        )


async def _mark_failed(
    document_id: int,
    error_code: str,
    error_message: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        result = await session.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            return
        document.status = DocumentStatus.FAILED.value
        document.error_code = error_code
        document.error_message = error_message
        document.chunk_count = 0
        await session.commit()
