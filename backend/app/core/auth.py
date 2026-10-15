from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise api_error(401, "authentication_required", "Authentication is required")

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        if payload.get("token_type") != "access" or not isinstance(subject, str):
            raise ValueError("Invalid token claims")
        user_id = int(subject)
        if user_id <= 0:
            raise ValueError("Invalid token subject")
    except (JWTError, TypeError, ValueError):
        raise api_error(401, "invalid_token", "The access token is invalid or expired")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise api_error(401, "invalid_token", "The access token is invalid or expired")
    return user


async def get_workspace_membership(
    workspace_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMember:
    result = await db.execute(
        select(WorkspaceMember)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.is_active.is_(True),
            Workspace.is_active.is_(True),
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        # A 404 avoids disclosing whether another tenant exists.
        raise api_error(404, "workspace_not_found", "Workspace not found")
    return membership


async def require_workspace_admin(
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
) -> WorkspaceMember:
    if membership.role != WorkspaceRole.ADMIN.value:
        raise api_error(
            403,
            "insufficient_role",
            "Workspace administrator role is required",
        )
    return membership


async def require_document_manager(
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
) -> WorkspaceMember:
    if membership.role not in {
        WorkspaceRole.ADMIN.value,
        WorkspaceRole.SUPPORT_AGENT.value,
    }:
        raise api_error(
            403,
            "insufficient_role",
            "Workspace administrator or support agent role is required",
        )
    return membership
