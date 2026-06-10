import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class WorkflowExecution(Base):
    """One recorded run of a workflow, written by the webhook background task."""

    __tablename__ = "workflow_executions"

    execution_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.workflow_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success|error
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
