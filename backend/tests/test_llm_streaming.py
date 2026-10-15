from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import llm


@pytest.mark.asyncio
async def test_groq_wrapper_yields_sdk_deltas_and_closes_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="there"))]),
    ]

    class FakeAsyncStream:
        closed = False

        def __aiter__(self) -> AsyncIterator[Any]:
            async def iterate() -> AsyncIterator[Any]:
                for chunk in chunks:
                    yield chunk

            return iterate()

        async def close(self) -> None:
            self.closed = True

    fake_stream = FakeAsyncStream()
    calls: list[dict[str, Any]] = []

    class FakeCompletions:
        async def create(self, **kwargs: Any) -> FakeAsyncStream:
            calls.append(kwargs)
            return fake_stream

    monkeypatch.setattr(
        llm,
        "_groq_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        ),
    )
    output = [
        chunk
        async for chunk in llm.stream_groq(
            "prompt",
            model="configured-groq-model",
            system="system",
        )
    ]

    assert output == ["Hello ", "there"]
    assert calls[0]["stream"] is True
    assert calls[0]["model"] == "configured-groq-model"
    assert fake_stream.closed


@pytest.mark.asyncio
async def test_gemini_wrapper_uses_sdk_streaming_and_closes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeResponse:
        closed = False

        def __iter__(self):
            return iter(
                [
                    SimpleNamespace(text="First"),
                    SimpleNamespace(text=" second"),
                    SimpleNamespace(text=""),
                ]
            )

        def close(self) -> None:
            self.closed = True

    response = FakeResponse()

    class FakeModel:
        def generate_content(self, *args: Any, **kwargs: Any) -> FakeResponse:
            calls.append({"args": args, **kwargs})
            return response

    monkeypatch.setattr(llm, "_gemini_model", lambda *_args: FakeModel())
    output = [
        chunk
        async for chunk in llm.stream_gemini(
            "prompt",
            model="configured-gemini-model",
            system="system",
        )
    ]

    assert output == ["First", " second"]
    assert calls[0]["stream"] is True
    assert calls[0]["args"] == ("prompt",)
    assert response.closed
