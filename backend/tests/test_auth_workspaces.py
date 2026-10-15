from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import get_db
from app.main import app
from app.models import Base, User
from app.models.workspace import WorkspaceRole
from app.core.security import verify_password


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.test_session_factory = session_factory

    async def override_get_db() -> AsyncIterator:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session_factory
        await engine.dispose()


async def register_user(
    client: AsyncClient,
    email: str,
    password: str = "correct-horse-battery",
) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "database_url",
    [
        "postgres://render-user:encoded%40pass@db.example:5432/app",
        "postgresql://render-user:encoded%40pass@db.example:5432/app",
    ],
)
async def test_render_database_url_uses_asyncpg_and_environment_overrides_file(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv(
        "SECRET_KEY",
        "test-secret-key-that-is-at-least-32-characters-long",
    )

    loaded_settings = Settings(_env_file=None)
    engine = create_async_engine(loaded_settings.DATABASE_URL)

    assert loaded_settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert loaded_settings.DATABASE_URL.endswith("@db.example:5432/app")
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"
    await engine.dispose()


def test_asyncpg_database_url_is_preserved() -> None:
    loaded_settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://user:pass@db.example:5432/app",
        SECRET_KEY="test-secret-key-that-is-at-least-32-characters-long",
    )

    assert loaded_settings.DATABASE_URL.startswith("postgresql+asyncpg://")


@pytest.mark.asyncio
async def test_register_hashes_password_and_login_protects_me(client: AsyncClient) -> None:
    user = await register_user(client, "Alice@example.com")
    assert user["email"] == "alice@example.com"
    assert "hashed_password" not in user

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ALICE@example.com", "password": "correct-horse-battery"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]
    assert "hashed_password" not in me.json()


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_and_weak_password(client: AsyncClient) -> None:
    await register_user(client, "duplicate@example.com")
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUPLICATE@example.com",
            "password": "correct-horse-battery",
            "full_name": "Duplicate",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_already_registered"

    invalid = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short", "full_name": "Weak"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_login_rejects_bad_credentials_and_me_requires_authentication(
    client: AsyncClient,
) -> None:
    await register_user(client, "login@example.com")
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "invalid_credentials"

    unauthenticated = await client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "authentication_required"

    missing_route = await client.get("/api/v1/not-a-route")
    assert missing_route.status_code == 404
    assert missing_route.json()["error"]["code"] == "http_404"


@pytest.mark.asyncio
async def test_health_liveness_probe(client: AsyncClient) -> None:
    liveness = await client.get("/api/v1/health")
    assert liveness.status_code == 200
    assert liveness.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_workspace_owner_is_admin_and_member_management_is_role_protected(
    client: AsyncClient,
) -> None:
    owner = await register_user(client, "owner@example.com")
    member = await register_user(client, "member@example.com")
    owner_token = await login(client, owner["email"], "correct-horse-battery")
    member_token = await login(client, member["email"], "correct-horse-battery")

    created = await client.post(
        "/api/v1/workspaces",
        json={"name": "Engineering", "description": "Private team"},
        headers=auth_header(owner_token),
    )
    assert created.status_code == 201, created.text
    workspace_id = created.json()["id"]
    assert created.json()["slug"] == "engineering"

    owner_members = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=auth_header(owner_token),
    )
    assert owner_members.status_code == 200
    assert owner_members.json()[0]["role"] == WorkspaceRole.ADMIN.value

    added = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": member["email"], "role": WorkspaceRole.SUPPORT_AGENT.value},
        headers=auth_header(owner_token),
    )
    assert added.status_code == 201, added.text
    assert added.json()["role"] == WorkspaceRole.SUPPORT_AGENT.value

    duplicate = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": member["email"], "role": WorkspaceRole.USER.value},
        headers=auth_header(owner_token),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "membership_already_exists"

    support_read = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(member_token),
    )
    assert support_read.status_code == 200

    settings_denied = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Not allowed", "description": "Support agents cannot update settings"},
        headers=auth_header(member_token),
    )
    assert settings_denied.status_code == 403
    assert settings_denied.json()["error"]["code"] == "insufficient_role"

    denied = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": owner["email"], "role": WorkspaceRole.USER.value},
        headers=auth_header(member_token),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_role"

    changed = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        json={"role": WorkspaceRole.USER.value},
        headers=auth_header(owner_token),
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == WorkspaceRole.USER.value

    removed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=auth_header(owner_token),
    )
    assert removed.status_code == 204

    last_admin = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner['id']}",
        headers=auth_header(owner_token),
    )
    assert last_admin.status_code == 409
    assert last_admin.json()["error"]["code"] == "owner_cannot_be_removed"

    owner_demotion = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{owner['id']}",
        json={"role": WorkspaceRole.USER.value},
        headers=auth_header(owner_token),
    )
    assert owner_demotion.status_code == 409
    assert owner_demotion.json()["error"]["code"] == "owner_role_required"


@pytest.mark.asyncio
async def test_member_can_read_workspace_but_cannot_cross_tenant_boundary(
    client: AsyncClient,
) -> None:
    first = await register_user(client, "first@example.com")
    second = await register_user(client, "second@example.com")
    first_token = await login(client, first["email"], "correct-horse-battery")
    second_token = await login(client, second["email"], "correct-horse-battery")

    first_workspace = await client.post(
        "/api/v1/workspaces",
        json={"name": "First Workspace"},
        headers=auth_header(first_token),
    )
    second_workspace = await client.post(
        "/api/v1/workspaces",
        json={"name": "Second Workspace"},
        headers=auth_header(second_token),
    )
    first_id = first_workspace.json()["id"]
    second_id = second_workspace.json()["id"]

    own = await client.get(
        f"/api/v1/workspaces/{first_id}",
        headers=auth_header(first_token),
    )
    assert own.status_code == 200
    own_workspaces = await client.get(
        "/api/v1/workspaces",
        headers=auth_header(first_token),
    )
    assert own_workspaces.status_code == 200
    assert [workspace["id"] for workspace in own_workspaces.json()] == [first_id]

    cross_workspace = await client.get(
        f"/api/v1/workspaces/{second_id}",
        headers=auth_header(first_token),
    )
    cross_members = await client.get(
        f"/api/v1/workspaces/{second_id}/members",
        headers=auth_header(first_token),
    )
    cross_write = await client.post(
        f"/api/v1/workspaces/{second_id}/members",
        json={"email": first["email"], "role": WorkspaceRole.USER.value},
        headers=auth_header(first_token),
    )
    assert [cross_workspace.status_code, cross_members.status_code, cross_write.status_code] == [
        404,
        404,
        404,
    ]
    assert cross_workspace.json()["error"]["code"] == "workspace_not_found"


@pytest.mark.asyncio
async def test_workspace_slug_conflict_is_reported_without_leaking_database_errors(
    client: AsyncClient,
) -> None:
    first = await register_user(client, "slug-one@example.com")
    second = await register_user(client, "slug-two@example.com")
    first_token = await login(client, first["email"], "correct-horse-battery")
    second_token = await login(client, second["email"], "correct-horse-battery")

    first_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Same Name"},
        headers=auth_header(first_token),
    )
    conflict = await client.post(
        "/api/v1/workspaces",
        json={"name": "Same Name"},
        headers=auth_header(second_token),
    )
    assert first_response.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "workspace_slug_conflict"


@pytest.mark.asyncio
async def test_workspace_analytics_and_settings_are_authorized(
    client: AsyncClient,
) -> None:
    owner = await register_user(client, "analytics-owner@example.com")
    outsider = await register_user(client, "analytics-outsider@example.com")
    owner_token = await login(client, owner["email"], "correct-horse-battery")
    outsider_token = await login(client, outsider["email"], "correct-horse-battery")
    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Analytics Workspace"},
        headers=auth_header(owner_token),
    )
    workspace_id = workspace_response.json()["id"]

    analytics = await client.get(
        f"/api/v1/workspaces/{workspace_id}/analytics",
        headers=auth_header(owner_token),
    )
    assert analytics.status_code == 200
    assert analytics.json() == {
        "document_count": 0,
        "documents_by_status": {},
        "conversation_count": 0,
        "active_member_count": 1,
    }

    updated = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Renamed Workspace", "description": "Updated settings"},
        headers=auth_header(owner_token),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Workspace"
    assert updated.json()["description"] == "Updated settings"

    denied_update = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Unauthorized Change", "description": None},
        headers=auth_header(outsider_token),
    )
    denied_analytics = await client.get(
        f"/api/v1/workspaces/{workspace_id}/analytics",
        headers=auth_header(outsider_token),
    )
    assert denied_update.status_code == 404
    assert denied_analytics.status_code == 404


@pytest.mark.asyncio
async def test_password_hash_is_persisted_not_plaintext(
    client: AsyncClient,
) -> None:
    password = "only-a-test-password"
    await register_user(client, "stored@example.com", password)
    async with app.state.test_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == "stored@example.com")
        )
        user = result.scalar_one()

    assert user.hashed_password != password
    assert user.hashed_password.startswith("$2")
    assert verify_password(password, user.hashed_password)
