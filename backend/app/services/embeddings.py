from __future__ import annotations

import math
import asyncio
from collections.abc import Sequence
from typing import Protocol

from app.config import settings
from app.models.document import EMBEDDING_DIMENSIONS


class EmbeddingProviderError(Exception):
    pass


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...

    async def embed_query(self, text: str) -> list[float]:
        ...


class GeminiEmbeddingProvider:
    def __init__(self) -> None:
        self.model = settings.EMBEDDING_MODEL

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            return await asyncio.to_thread(
                self._embed_sync,
                list(texts),
                "RETRIEVAL_DOCUMENT",
            )
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError("Gemini embedding request failed") from exc

    async def embed_query(self, text: str) -> list[float]:
        try:
            vectors = await asyncio.to_thread(
                self._embed_sync,
                [text],
                "RETRIEVAL_QUERY",
            )
            return vectors[0]
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError("Gemini query embedding failed") from exc

    def _embed_sync(
        self,
        texts: list[str],
        task_type: str,
    ) -> list[list[float]]:
        if not settings.GEMINI_API_KEY:
            raise EmbeddingProviderError("GEMINI_API_KEY is not configured")
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            response = genai.embed_content(
                model=self.model,
                content=texts,
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            )
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError("Gemini embedding request failed") from exc

        raw_vectors = response.get("embedding") if isinstance(response, dict) else None
        if not isinstance(raw_vectors, list) or len(raw_vectors) != len(texts):
            raise EmbeddingProviderError("Gemini returned an invalid embedding response")

        vectors: list[list[float]] = []
        for item in raw_vectors:
            values = item.get("values") if isinstance(item, dict) else item
            if (
                not isinstance(values, list)
                or len(values) != EMBEDDING_DIMENSIONS
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in values
                )
            ):
                raise EmbeddingProviderError(
                    f"Gemini must return {EMBEDDING_DIMENSIONS}-dimension vectors"
                )
            vectors.append([float(value) for value in values])
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()
