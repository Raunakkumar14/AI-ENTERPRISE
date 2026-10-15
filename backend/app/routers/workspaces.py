from __future__ import annotations

import re
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_user,
    get_workspace_membership,
    require_workspace_admin,
)
from app.core.errors import api_error
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.conversation import Conversation
from app.models.document import Document
from app.schemas.workspace import (
    MemberCreate,
    MemberRead,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceListItem,
    WorkspaceRead,
    WorkspaceAnalytics,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _workspace_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"workspace-{secrets.token_hex(4)}"


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    workspace = Workspace(
        name=request.name,
        slug=_workspace_slug(request.name),
        description=request.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    try:
        await db.flush()
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=current_user.id,
                role=WorkspaceRole.ADMIN.value,
            )
        )
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint_name != "ix_workspaces_slug" and "UNIQUE constraint failed: workspaces.slug" not in str(exc.orig):
            raise
        raise api_error(
            409,
            "workspace_slug_conflict",
            "A workspace with a matching name already exists",
        )
    return workspace


@router.get("", response_model=list[WorkspaceListItem], summary="List your workspaces")
async def list_workspaces(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkspaceListItem]:
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.is_active.is_(True),
            Workspace.is_active.is_(True),
        )
        .order_by(Workspace.id)
    )
    return [
        WorkspaceListItem.model_validate(
            {**WorkspaceRead.model_validate(workspace).model_dump(), "role": role}
        )
        for workspace, role in result.all()
    ]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Get workspace details",
)
async def get_workspace(
    workspace_id: int,
    membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == membership.workspace_id,
            Workspace.is_active.is_(True),
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    return workspace


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Update workspace settings",
)
async def update_workspace(
    workspace_id: int,
    request: WorkspaceUpdate,
    admin: Annotated[WorkspaceMember, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    workspace = await _lock_workspace_for_admin(db, workspace_id, admin.id)
    workspace.name = request.name
    workspace.description = request.description
    await db.flush()
    return workspace


@router.get(
    "/{workspace_id}/analytics",
    response_model=WorkspaceAnalytics,
    summary="Get workspace analytics",
)
async def get_workspace_analytics(
    workspace_id: int,
    _membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceAnalytics:
    document_counts = await db.execute(
        select(Document.status, func.count(Document.id))
        .where(Document.workspace_id == workspace_id)
        .group_by(Document.status)
    )
    documents_by_status = {status: count for status, count in document_counts.all()}
    conversation_count = await db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.workspace_id == workspace_id
        )
    )
    active_member_count = await db.scalar(
        select(func.count(WorkspaceMember.id))
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    return WorkspaceAnalytics(
        document_count=sum(documents_by_status.values()),
        documents_by_status=documents_by_status,
        conversation_count=conversation_count or 0,
        active_member_count=active_member_count or 0,
    )


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberRead],
    summary="List workspace members",
)
async def list_members(
    workspace_id: int,
    _membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MemberRead]:
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at, WorkspaceMember.user_id)
    )
    return [
        MemberRead(
            user_id=member.user_id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            is_active=member.is_active and user.is_active,
            joined_at=member.joined_at,
        )
        for member, user in result.all()
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to a workspace",
)
async def add_member(
    workspace_id: int,
    request: MemberCreate,
    _admin: Annotated[WorkspaceMember, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemberRead:
    await _lock_workspace_for_admin(db, workspace_id, _admin.id)
    user_result = await db.execute(
        select(User).where(User.email == request.email, User.is_active.is_(True))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise api_error(404, "user_not_found", "Active user not found")

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=request.role.value,
    )
    db.add(member)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        sqlite_unique_error = (
            "UNIQUE constraint failed: workspace_members.workspace_id, "
            "workspace_members.user_id"
        )
        if constraint_name != "uq_workspace_user" and sqlite_unique_error not in str(exc.orig):
            raise
        raise api_error(
            409,
            "membership_already_exists",
            "The user is already a member of this workspace",
        )
    return MemberRead(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        is_active=member.is_active,
        joined_at=member.joined_at,
    )


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberRead,
    summary="Change a workspace member's role",
)
async def update_member_role(
    workspace_id: int,
    user_id: int,
    request: MemberRoleUpdate,
    _admin: Annotated[WorkspaceMember, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemberRead:
    workspace = await _lock_workspace_for_admin(db, workspace_id, _admin.id)
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    pair = result.one_or_none()
    if pair is None:
        raise api_error(404, "member_not_found", "Workspace member not found")
    member, user = pair

    if user_id == workspace.owner_id and request.role != WorkspaceRole.ADMIN:
        raise api_error(409, "owner_role_required", "The workspace owner must remain an administrator")

    if member.role == WorkspaceRole.ADMIN.value and request.role != WorkspaceRole.ADMIN:
        await _ensure_another_admin(db, workspace_id, user_id)

    member.role = request.role.value
    await db.flush()
    return MemberRead(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        is_active=member.is_active and user.is_active,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a user from a workspace",
)
async def remove_member(
    workspace_id: int,
    user_id: int,
    _admin: Annotated[WorkspaceMember, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    workspace = await _lock_workspace_for_admin(db, workspace_id, _admin.id)
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise api_error(404, "member_not_found", "Workspace member not found")

    if workspace.owner_id == user_id:
        raise api_error(409, "owner_cannot_be_removed", "The workspace owner cannot be removed")

    if member.role == WorkspaceRole.ADMIN.value:
        await _ensure_another_admin(db, workspace_id, user_id)

    await db.delete(member)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _lock_workspace_for_admin(
    db: AsyncSession,
    workspace_id: int,
    admin_membership_id: int,
) -> Workspace:
    workspace_result = await db.execute(
        select(Workspace)
        .where(Workspace.id == workspace_id, Workspace.is_active.is_(True))
        .with_for_update()
    )
    workspace = workspace_result.scalar_one_or_none()
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")

    membership_result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.id == admin_membership_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_active.is_(True),
        )
        .execution_options(populate_existing=True)
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if membership.role != WorkspaceRole.ADMIN.value:
        raise api_error(
            403,
            "insufficient_role",
            "Workspace administrator role is required",
        )
    return workspace


async def _ensure_another_admin(
    db: AsyncSession,
    workspace_id: int,
    departing_user_id: int,
) -> None:
    result = await db.execute(
        select(WorkspaceMember.user_id)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id != departing_user_id,
            WorkspaceMember.role == WorkspaceRole.ADMIN.value,
            WorkspaceMember.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    if result.first() is None:
        raise api_error(
            409,
            "last_admin_required",
            "A workspace must retain at least one active administrator",
        )
