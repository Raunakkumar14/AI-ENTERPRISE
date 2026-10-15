from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.auth import get_workspace_membership
from app.core.errors import api_error
from app.database import get_db
from app.models.conversation import Conversation, ConversationMessage
from app.models.workspace import WorkspaceMember
from app.schemas.rag import (
    AskRequest,
    AskResponse,
    CitationRead,
    ConversationDetail,
    ConversationList,
    ConversationRead,
    MessageRead,
)
from app.services.embeddings import (
    EmbeddingProvider,
    EmbeddingProviderError,
    get_embedding_provider,
)
from app.services.rag import (
    UNCERTAIN_ANSWER,
    RagIncompleteResponseError,
    RagProviderError,
    answer_question,
    retrieve_relevant_chunks,
    stream_grounded_response,
    validate_grounded_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["RAG"])
_STREAM_FAILURE_MESSAGE = "I couldn't complete the answer. Please try again."


async def _get_conversation_and_history(
    db: AsyncSession,
    workspace_id: int,
    user_id: int,
    request: AskRequest,
) -> tuple[Conversation, list[dict[str, str]]]:
    if request.conversation_id is None:
        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=request.question.strip()[:255],
        )
        db.add(conversation)
        await db.flush()
        return conversation, []

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == request.conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise api_error(404, "conversation_not_found", "Conversation not found")

    messages_result = await db.execute(
        select(ConversationMessage.role, ConversationMessage.content)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.id.desc())
        .limit(20)
    )
    return conversation, [
        {"role": role, "content": content[-4000:]}
        for role, content in reversed(messages_result.all())
    ]


def _sse_event(event: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question using workspace documents",
)
async def ask_workspace(
    workspace_id: int,
    request: AskRequest,
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise api_error(422, "invalid_question", "Question must not be blank")

    conversation, history = await _get_conversation_and_history(
        db,
        workspace_id,
        membership.user_id,
        request,
    )

    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=question,
            citations=[],
        )
    )
    await db.commit()

    try:
        answer, cited_sources = await answer_question(
            db,
            embedding_provider,
            workspace_id,
            question,
            history,
        )
    except RagProviderError as exc:
        logger.error("RAG provider request failed (%s)", type(exc).__name__)
        db.add(
            ConversationMessage(
                conversation_id=conversation.id,
                role="assistant",
                content="I couldn't generate an answer right now. Please try again later.",
                citations=[],
            )
        )
        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise api_error(
            503,
            "rag_provider_unavailable",
            "A configured RAG provider is unavailable; try again later",
        ) from exc

    citations = [source.citation() for source in cited_sources]
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            citations=citations,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return AskResponse(
        conversation_id=conversation.id,
        answer=answer,
        citations=[CitationRead(**citation) for citation in citations],
        insufficient_context=not bool(citations),
    )


@router.post(
    "/ask/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream a grounded answer using server-sent events",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_workspace_answer(
    workspace_id: int,
    request: AskRequest,
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> StreamingResponse:
    question = request.question.strip()
    if not question:
        raise api_error(422, "invalid_question", "Question must not be blank")

    conversation, history = await _get_conversation_and_history(
        db,
        workspace_id,
        membership.user_id,
        request,
    )
    conversation_id = conversation.id
    conversation_title = conversation.title
    db.add(
        ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=question,
            citations=[],
        )
    )
    await db.commit()

    async def event_stream() -> AsyncIterator[str]:
        completed = False
        yield _sse_event(
            "conversation",
            {"conversation_id": conversation_id, "title": conversation_title},
        )
        try:
            try:
                query_embedding = await embedding_provider.embed_query(question)
            except EmbeddingProviderError as exc:
                raise RagProviderError("Question embedding could not be generated") from exc

            sources = await retrieve_relevant_chunks(
                db,
                workspace_id,
                query_embedding,
            )
            if not sources:
                await db.rollback()
                saved_conversation = await db.get(Conversation, conversation_id)
                if saved_conversation is None:
                    raise RagProviderError("Conversation disappeared during streaming")
                answer = UNCERTAIN_ANSWER
                citations: list[dict[str, object]] = []
                db.add(
                    ConversationMessage(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        citations=citations,
                    )
                )
                saved_conversation.updated_at = datetime.now(timezone.utc)
                await db.commit()
                completed = True
                yield _sse_event("text", {"delta": answer})
                yield _sse_event(
                    "citations",
                    {"items": citations, "insufficient_context": True},
                )
                yield _sse_event(
                    "complete",
                    {
                        "conversation_id": conversation_id,
                        "answer": answer,
                        "citations": citations,
                        "status": "completed",
                    },
                )
                return

            await db.rollback()
            raw_response = ""
            grounded_stream = stream_grounded_response(question, sources, history)
            try:
                async for chunk in grounded_stream:
                    raw_response = chunk.response_text
                    if chunk.delta:
                        yield _sse_event("text", {"delta": chunk.delta})
            finally:
                await grounded_stream.aclose()

            answer, cited_sources = validate_grounded_response(raw_response, sources)
            if not cited_sources and answer == UNCERTAIN_ANSWER and not raw_response:
                raise RagIncompleteResponseError("The provider returned an empty response")
            citations = [source.citation() for source in cited_sources]
            if not cited_sources:
                answer = UNCERTAIN_ANSWER

            saved_conversation = await db.get(Conversation, conversation_id)
            if saved_conversation is None:
                raise RagProviderError("Conversation disappeared during streaming")
            db.add(
                ConversationMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                    citations=citations,
                )
            )
            saved_conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()
            completed = True
            yield _sse_event(
                "citations",
                {"items": citations, "insufficient_context": not bool(citations)},
            )
            yield _sse_event(
                "complete",
                {
                    "conversation_id": conversation_id,
                    "answer": answer,
                    "citations": citations,
                    "status": "completed",
                },
            )
        except RagProviderError as exc:
            logger.error("RAG stream failed (%s)", type(exc).__name__)
            await db.rollback()
            failed_conversation = await db.get(Conversation, conversation_id)
            if failed_conversation is None:
                raise
            db.add(
                ConversationMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=_STREAM_FAILURE_MESSAGE,
                    citations=[],
                )
            )
            failed_conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()
            completed = True
            code = (
                "incomplete_response"
                if isinstance(exc, RagIncompleteResponseError)
                else "provider_unavailable"
            )
            yield _sse_event(
                "error",
                {"code": code, "message": _STREAM_FAILURE_MESSAGE},
            )
            yield _sse_event(
                "complete",
                {"conversation_id": conversation_id, "status": "failed"},
            )
        except Exception as exc:
            logger.error(
                "Unexpected RAG streaming error (%s)",
                type(exc).__name__,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            await db.rollback()
            yield _sse_event(
                "error",
                {
                    "code": "stream_failed",
                    "message": "The answer could not be completed. Please try again.",
                },
            )
            yield _sse_event(
                "complete",
                {"conversation_id": conversation_id, "status": "failed"},
            )
        finally:
            if not completed:
                await db.rollback()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=ConversationList)
async def list_conversations(
    workspace_id: int,
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationList:
    filters = (
        Conversation.workspace_id == workspace_id,
        Conversation.user_id == membership.user_id,
    )
    total_result = await db.execute(
        select(func.count(Conversation.id)).where(*filters)
    )
    result = await db.execute(
        select(Conversation)
        .where(*filters)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ConversationList(
        items=list(result.scalars().all()),
        total=total_result.scalar_one(),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
async def get_conversation(
    workspace_id: int,
    conversation_id: int,
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationDetail:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == membership.user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise api_error(404, "conversation_not_found", "Conversation not found")

    messages_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.id)
    )
    return ConversationDetail(
        **ConversationRead.model_validate(conversation).model_dump(),
        messages=[
            MessageRead.model_validate(message)
            for message in messages_result.scalars().all()
        ],
    )
