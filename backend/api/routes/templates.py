from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.models.template import WorkflowTemplate
from backend.schemas.template import TemplateResponse

router = APIRouter(prefix="/v1/templates", tags=["templates"])

NicheParam = Literal["accounting", "trade", "real_estate", "logistics", "healthcare"]


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    niche: NicheParam | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WorkflowTemplate]:
    try:
        query = select(WorkflowTemplate).order_by(
            WorkflowTemplate.niche, WorkflowTemplate.slug
        )
        if niche is not None:
            query = query.where(WorkflowTemplate.niche == niche)
        return list(db.execute(query).scalars().all())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template lookup failed",
        ) from exc
