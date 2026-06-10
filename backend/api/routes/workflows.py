from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models.user import User
from backend.models.workflow import Workflow
from backend.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowUpdateRequest,
)

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


def _get_owned_workflow(db: Session, user: User, workflow_id: str) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None or workflow.user_id != user.user_id:
        # 404 for foreign workflows too — don't leak existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Workflow]:
    try:
        return list(
            db.execute(
                select(Workflow)
                .where(Workflow.user_id == user.user_id)
                .order_by(Workflow.created_at.desc())
            )
            .scalars()
            .all()
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List failed"
        ) from exc


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    body: WorkflowCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    try:
        workflow = Workflow(
            user_id=user.user_id,
            name=body.name,
            niche=body.niche,
            status=body.status,
            steps=[step.model_dump() for step in body.steps],
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Create failed"
        ) from exc


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    return _get_owned_workflow(db, user, workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    body: WorkflowUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    workflow = _get_owned_workflow(db, user, workflow_id)
    try:
        if body.name is not None:
            workflow.name = body.name
        if body.niche is not None:
            workflow.niche = body.niche
        if body.status is not None:
            workflow.status = body.status
        if body.steps is not None:
            workflow.steps = [step.model_dump() for step in body.steps]
        db.commit()
        db.refresh(workflow)
        return workflow
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed"
        ) from exc


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    workflow = _get_owned_workflow(db, user, workflow_id)
    try:
        db.delete(workflow)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete failed"
        ) from exc
