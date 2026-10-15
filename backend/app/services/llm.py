"""
backend/app/services/llm.py
────────────────────────────
Thin, beginner-friendly wrappers for the Groq and Gemini APIs.

Both clients are lazily initialised — they are only created the first
time a function is called, so importing this module is always safe even
when the API keys are not yet set.

Usage (in a future router):
    from app.services.llm import ask_groq, ask_gemini

    answer = await ask_groq("Explain RAG in one sentence.")
    answer = await ask_gemini("What is pgvector used for?")
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Optional

from app.config import settings


# ── Groq ─────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _groq_client():
    """
    Return a cached Groq client.
    Raises RuntimeError if GROQ_API_KEY is not set in .env.
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env and restart the server."
        )
    from groq import AsyncGroq  # imported lazily so missing key fails gracefully
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


async def ask_groq(
    prompt: str,
    *,
    system: str = "You are a helpful enterprise knowledge assistant.",
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """
    Send a single-turn prompt to Groq and return the text response.

    Parameters
    ----------
    prompt      : The user's question or instruction.
    system      : System message that sets the assistant's persona.
    model       : Override the default model from settings.
    max_tokens  : Maximum tokens in the response.
    temperature : Sampling temperature (0 = deterministic, 1 = creative).

    Returns
    -------
    str : The assistant's text reply.

    Example
    -------
    answer = await ask_groq("Summarise the attached document.")
    """
    client = _groq_client()
    chosen_model = model or settings.GROQ_MODEL

    response = await client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def stream_groq(
    prompt: str,
    *,
    system: str,
    model: Optional[str] = None,
    max_tokens: int = 1200,
    temperature: float = 0.1,
) -> AsyncIterator[str]:
    client = _groq_client()
    stream = await client.chat.completions.create(
        model=model or settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    try:
        async for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
    finally:
        await stream.close()


# ── Google Gemini ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _gemini_model(model_name: str, system: str):
    """
    Return a cached Gemini GenerativeModel instance.
    Raises RuntimeError if GEMINI_API_KEY is not set in .env.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env and restart the server."
        )
    import google.generativeai as genai  # lazily imported
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(model_name, system_instruction=system)


async def ask_gemini(
    prompt: str,
    *,
    system: str = "You are a helpful enterprise knowledge assistant.",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_output_tokens: int = 1024,
) -> str:
    """
    Send a prompt to Google Gemini and return the text response.

    Parameters
    ----------
    prompt            : The user's question or instruction.
    model             : Override the default model from settings.
    temperature       : Sampling temperature.
    max_output_tokens : Maximum tokens in the response.

    Returns
    -------
    str : The model's text reply.

    Example
    -------
    answer = await ask_gemini("List the key points from this document.")
    """
    import asyncio

    chosen_model = model or settings.GEMINI_MODEL
    gen_model = _gemini_model(chosen_model, system)

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }

    # google-generativeai is sync — run it in the default executor
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: gen_model.generate_content(
            prompt,
            generation_config=generation_config,
        ),
    )
    return response.text or ""


async def stream_gemini(
    prompt: str,
    *,
    system: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_output_tokens: int = 1200,
) -> AsyncIterator[str]:
    chosen_model = model or settings.GEMINI_MODEL
    gen_model = _gemini_model(chosen_model, system)
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    response = await asyncio.to_thread(
        lambda: gen_model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=True,
        )
    )
    iterator = iter(response)
    sentinel = object()

    def next_chunk():
        return next(iterator, sentinel)

    try:
        while True:
            chunk = await asyncio.to_thread(next_chunk)
            if chunk is sentinel:
                break
            content = getattr(chunk, "text", None)
            if content:
                yield content
    finally:
        resources = (iterator, getattr(response, "_iterator", None), response)
        closed: set[int] = set()
        for resource in resources:
            close = getattr(resource, "close", None)
            if close is not None and id(resource) not in closed:
                closed.add(id(resource))
                await asyncio.to_thread(close)
