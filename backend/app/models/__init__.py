# backend/app/models/__init__.py
"""
Import all ORM models here so Alembic's autogenerate can discover them.

Example (add as you create new models):
    from app.models.document import Document  # noqa: F401
    from app.models.chunk import Chunk         # noqa: F401
"""

from app.models.base import Base, TimestampMixin  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace, WorkspaceMember  # noqa: F401
from app.models.document import Document, DocumentChunk, DocumentStatus  # noqa: F401
from app.models.conversation import Conversation, ConversationMessage  # noqa: F401
