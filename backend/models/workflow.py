import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Workflow(Base):
    __tablename__ = "workflows"

    workflow_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    # Unique key webhook triggers are addressed by: POST /v1/triggers/webhook/{route_key}
    route_key: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=_new_uuid, nullable=False
    )
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="workflows")  # noqa: F821
