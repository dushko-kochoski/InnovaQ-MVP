import uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    template_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Stable identifier, e.g. "invoice_reminder" — used by seed.py for idempotency
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
