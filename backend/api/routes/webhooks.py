import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.core.workflow_engine import execute_workflow
from backend.core.workflow_parser import WorkflowParseError
from backend.database.session import SessionLocal
from backend.models.execution import WorkflowExecution
from backend.models.user import User
from backend.models.workflow import Workflow
from backend.schemas.execution import ExecutionResponse

logger = logging.getLogger("innovaq.webhooks")

router = APIRouter(prefix="/v1/triggers", tags=["triggers"])


def run_workflow_steps(workflow_id: str, raw_steps: list, payload: dict) -> None:
    """Background task: execute the workflow, log the outcome, record the run."""
    run_status = "success"
    results: list = []
    try:
        results = execute_workflow(raw_steps, payload)
        logger.info("workflow %s executed: %s", workflow_id, results)
    except WorkflowParseError as exc:
        run_status = "error"
        results = [{"error": f"invalid steps: {exc}"}]
        logger.error("workflow %s has invalid steps: %s", workflow_id, exc)
    except Exception:
        run_status = "error"
        results = [{"error": "execution failed"}]
        logger.exception("workflow %s execution failed", workflow_id)

    # Module-level SessionLocal (not the request session) — the request's DB
    # session is already closed by the time background tasks run. Tests patch
    # this symbol to point at the in-memory test engine.
    try:
        with SessionLocal() as db:
            db.add(
                WorkflowExecution(
                    workflow_id=workflow_id, status=run_status, results=results
                )
            )
            db.commit()
    except Exception:
        logger.exception("failed to record execution for workflow %s", workflow_id)


@router.post("/webhook/{route_key}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    route_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    try:
        workflow = db.execute(
            select(Workflow).where(
                Workflow.route_key == route_key, Workflow.status == "active"
            )
        ).scalar_one_or_none()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lookup failed"
        ) from exc

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workflow for this route key",
        )

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {"data": payload}
    except Exception:
        payload = {}

    # Execute in the background — the caller gets an immediate ack.
    background_tasks.add_task(
        run_workflow_steps, workflow.workflow_id, workflow.steps, payload
    )
    return {"status": "accepted"}


@router.get("/recent", response_model=list[ExecutionResponse])
def recent_triggers(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Most recent workflow runs for the current user's workflows."""
    try:
        rows = db.execute(
            select(WorkflowExecution, Workflow.name)
            .join(Workflow, Workflow.workflow_id == WorkflowExecution.workflow_id)
            .where(Workflow.user_id == user.user_id)
            .order_by(WorkflowExecution.triggered_at.desc())
            .limit(limit)
        ).all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Execution lookup failed",
        ) from exc
    return [
        {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "workflow_name": workflow_name,
            "status": execution.status,
            "results": execution.results,
            "triggered_at": execution.triggered_at,
        }
        for execution, workflow_name in rows
    ]
