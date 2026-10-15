from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base, User
from app.models.document import Document, DocumentChunk
from app.models.workspace import WorkspaceRole
from app.routers.documents import get_document_session_factory
from app.services.embeddings import (
    EmbeddingProviderError,
    get_embedding_provider,
)


class FakeEmbeddingProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.fail:
            raise EmbeddingProviderError("provider secret error details")
        return [[0.25] * 1536 for _ in texts]


class InvalidEmbeddingProvider:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.25] for _ in texts]


@pytest_asyncio.fixture
async def document_client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_db] = _make_db_override(session_factory)
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[get_document_session_factory] = lambda: session_factory
    app.state.document_test_session_factory = session_factory
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        del app.state.document_test_session_factory
        await engine.dispose()


def _make_db_override(session_factory: async_sessionmaker):
    async def override_get_db() -> AsyncIterator:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return override_get_db


async def _register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "document-test-password",
            "full_name": email.split("@")[0],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _token(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "document-test-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _workspace(client: AsyncClient, token: str, name: str) -> int:
    response = await client.post(
        "/api/v1/workspaces",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _upload(
    client: AsyncClient,
    workspace_id: int,
    token: str,
    filename: str,
    content: bytes,
) -> Response:
    return await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=_bearer(token),
        files={"file": (filename, content)},
    )


@pytest.mark.asyncio
async def test_markdown_upload_chunks_and_embeddings_are_stored_and_deletable(
    document_client: AsyncClient,
) -> None:
    user = await _register(document_client, "documents@example.com")
    token = await _token(document_client, user["email"])
    workspace_id = await _workspace(document_client, token, "Ingestion")
    content = (("alpha-beta-" * 150) + "\n# End\n").encode()

    uploaded = await _upload(
        document_client,
        workspace_id,
        token,
        "notes.md",
        content,
    )
    assert uploaded.status_code == 202, uploaded.text
    assert uploaded.json()["status"] == "pending"
    document_id = uploaded.json()["id"]

    detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}",
        headers=_bearer(token),
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "completed"
    assert body["file_type"] == "markdown"
    assert body["sha256"]
    assert body["chunk_count"] > 1
    assert [chunk["chunk_index"] for chunk in body["chunks"]] == list(
        range(body["chunk_count"])
    )
    assert all(chunk["page_number"] is None for chunk in body["chunks"])
    assert body["chunks"][0]["content"][-200:] == body["chunks"][1]["content"][:200]

    async with app.state.document_test_session_factory() as session:
        document = await session.get(Document, document_id)
        result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        chunks = result.scalars().all()
        assert document is not None
        assert len(chunks) == body["chunk_count"]
        assert len(chunks[0].embedding) == 1536
        assert chunks[0].embedding[0] == 0.25

    listed = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=_bearer(token),
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == document_id

    deleted = await document_client.delete(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}",
        headers=_bearer(token),
    )
    assert deleted.status_code == 204
    missing = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}",
        headers=_bearer(token),
    )
    assert missing.status_code == 404


def _make_pdf(pages: list[str]) -> bytes:
    font_id = 3 + len(pages) * 2
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{' '.join(f'{3 + i * 2} 0 R' for i in range(len(pages)))}] "
            f"/Count {len(pages)} >>"
        ).encode(),
    ]
    for index, text in enumerate(pages):
        page_id = 3 + index * 2
        content_id = page_id + 1
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode(),
                b"<< /Length "
                + str(len(stream)).encode()
                + b" >>\nstream\n"
                + stream
                + b"\nendstream",
            ]
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


@pytest.mark.asyncio
async def test_pdf_upload_preserves_page_numbers(document_client: AsyncClient) -> None:
    user = await _register(document_client, "pdf@example.com")
    token = await _token(document_client, user["email"])
    workspace_id = await _workspace(document_client, token, "PDF")
    uploaded = await _upload(
        document_client,
        workspace_id,
        token,
        "manual.pdf",
        _make_pdf(["Page one content.", "Page two content."]),
    )
    assert uploaded.status_code == 202, uploaded.text

    detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{uploaded.json()['id']}",
        headers=_bearer(token),
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["page_count"] == 2
    assert [chunk["page_number"] for chunk in detail.json()["chunks"]] == [1, 2]


@pytest.mark.asyncio
async def test_plain_text_upload_completes_without_page_numbers(
    document_client: AsyncClient,
) -> None:
    user = await _register(document_client, "plain-text@example.com")
    token = await _token(document_client, user["email"])
    workspace_id = await _workspace(document_client, token, "Plain Text")
    uploaded = await _upload(
        document_client,
        workspace_id,
        token,
        "notes.txt",
        b"UTF-8 plain text document.",
    )
    assert uploaded.status_code == 202

    detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{uploaded.json()['id']}",
        headers=_bearer(token),
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["file_type"] == "text"
    assert detail.json()["chunks"][0]["content"] == "UTF-8 plain text document."
    assert detail.json()["chunks"][0]["page_number"] is None


@pytest.mark.asyncio
async def test_document_upload_validation_and_parse_failure_are_safe(
    document_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await _register(document_client, "validation@example.com")
    token = await _token(document_client, user["email"])
    workspace_id = await _workspace(document_client, token, "Validation")

    unsupported = await _upload(
        document_client,
        workspace_id,
        token,
        "script.py",
        b"print('no')",
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_file_type"

    empty = await _upload(document_client, workspace_id, token, "empty.txt", b"")
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "empty_file"

    monkeypatch.setattr(settings, "MAX_DOCUMENT_SIZE_MB", 1)
    oversized = await _upload(
        document_client,
        workspace_id,
        token,
        "large.txt",
        b"x" * (1024 * 1024 + 1),
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "file_too_large"
    monkeypatch.undo()

    invalid_text = await _upload(
        document_client,
        workspace_id,
        token,
        "invalid.txt",
        b"\xff\xfe",
    )
    assert invalid_text.status_code == 202
    detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{invalid_text.json()['id']}",
        headers=_bearer(token),
    )
    assert detail.json()["status"] == "failed"
    assert detail.json()["error_code"] == "document_parse_failed"
    assert "traceback" not in detail.text.lower()

    invalid_pdf = await _upload(
        document_client,
        workspace_id,
        token,
        "broken.pdf",
        b"%PDF-not-a-real-document",
    )
    assert invalid_pdf.status_code == 202
    pdf_detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{invalid_pdf.json()['id']}",
        headers=_bearer(token),
    )
    assert pdf_detail.json()["status"] == "failed"
    assert pdf_detail.json()["error_code"] == "document_parse_failed"


@pytest.mark.asyncio
async def test_embedding_errors_mark_document_failed_without_leaking_provider_details(
    document_client: AsyncClient,
) -> None:
    app.dependency_overrides[get_embedding_provider] = (
        lambda: FakeEmbeddingProvider(fail=True)
    )
    user = await _register(document_client, "provider-error@example.com")
    token = await _token(document_client, user["email"])
    workspace_id = await _workspace(document_client, token, "Provider Error")
    uploaded = await _upload(
        document_client,
        workspace_id,
        token,
        "notes.txt",
        b"Readable plain text.",
    )
    detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{uploaded.json()['id']}",
        headers=_bearer(token),
    )
    assert detail.json()["status"] == "failed"
    assert detail.json()["error_code"] == "embedding_failed"
    assert "secret error details" not in detail.text

    app.dependency_overrides[get_embedding_provider] = (
        lambda: InvalidEmbeddingProvider()
    )
    invalid_vectors = await _upload(
        document_client,
        workspace_id,
        token,
        "invalid-vectors.txt",
        b"Text with invalid embedding vector.",
    )
    invalid_detail = await document_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{invalid_vectors.json()['id']}",
        headers=_bearer(token),
    )
    assert invalid_detail.json()["status"] == "failed"
    assert invalid_detail.json()["error_code"] == "embedding_failed"


@pytest.mark.asyncio
async def test_cross_workspace_document_access_and_user_role_are_denied(
    document_client: AsyncClient,
) -> None:
    owner_a = await _register(document_client, "workspace-a@example.com")
    owner_b = await _register(document_client, "workspace-b@example.com")
    regular_user = await _register(document_client, "read-only@example.com")
    token_a = await _token(document_client, owner_a["email"])
    token_b = await _token(document_client, owner_b["email"])
    token_regular = await _token(document_client, regular_user["email"])
    workspace_a = await _workspace(document_client, token_a, "Workspace A")
    workspace_b = await _workspace(document_client, token_b, "Workspace B")

    uploaded = await _upload(
        document_client,
        workspace_a,
        token_a,
        "tenant.txt",
        b"Workspace A only.",
    )
    document_id = uploaded.json()["id"]
    cross_read = await document_client.get(
        f"/api/v1/workspaces/{workspace_a}/documents/{document_id}",
        headers=_bearer(token_b),
    )
    cross_delete = await document_client.delete(
        f"/api/v1/workspaces/{workspace_a}/documents/{document_id}",
        headers=_bearer(token_b),
    )
    assert cross_read.status_code == cross_delete.status_code == 404

    added = await document_client.post(
        f"/api/v1/workspaces/{workspace_a}/members",
        headers=_bearer(token_a),
        json={"email": regular_user["email"], "role": WorkspaceRole.USER.value},
    )
    assert added.status_code == 201
    visible = await document_client.get(
        f"/api/v1/workspaces/{workspace_a}/documents/{document_id}",
        headers=_bearer(token_regular),
    )
    assert visible.status_code == 200
    upload_denied = await _upload(
        document_client,
        workspace_a,
        token_regular,
        "denied.txt",
        b"No upload permission.",
    )
    delete_denied = await document_client.delete(
        f"/api/v1/workspaces/{workspace_a}/documents/{document_id}",
        headers=_bearer(token_regular),
    )
    assert upload_denied.status_code == delete_denied.status_code == 403

    promote = await document_client.patch(
        f"/api/v1/workspaces/{workspace_a}/members/{regular_user['id']}",
        headers=_bearer(token_a),
        json={"role": WorkspaceRole.SUPPORT_AGENT.value},
    )
    assert promote.status_code == 200
    support_upload = await _upload(
        document_client,
        workspace_a,
        token_regular,
        "support.txt",
        b"Support agent document.",
    )
    assert support_upload.status_code == 202
    support_delete = await document_client.delete(
        f"/api/v1/workspaces/{workspace_a}/documents/{support_upload.json()['id']}",
        headers=_bearer(token_regular),
    )
    assert support_delete.status_code == 204

    empty_list = await document_client.get(
        f"/api/v1/workspaces/{workspace_b}/documents",
        headers=_bearer(token_b),
    )
    assert empty_list.json()["total"] == 0
