"""Trigger → Condition → Action executor.

Steps run in order. A condition that evaluates false stops execution.
Trigger steps are skipped at run time (the trigger already fired — that is
why we are executing). Each run returns a list of per-step result dicts so
callers and tests can inspect exactly what happened.
"""

import logging
from typing import Any, Callable

import httpx

from backend.config import settings
from backend.core.workflow_parser import parse_steps
from backend.schemas.workflow import WorkflowStep

logger = logging.getLogger("innovaq.engine")

_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "contains": lambda a, b: b in a,
}


def evaluate_condition(step: WorkflowStep, payload: dict) -> bool:
    """Evaluate a condition step against the trigger payload.

    A missing field or a type mismatch evaluates to False (the workflow
    simply does not proceed) rather than raising.
    """
    if step.field not in payload:
        return False
    actual = payload[step.field]
    try:
        return _OPERATORS[step.operator](actual, step.value)
    except TypeError:
        return False


def execute_action(step: WorkflowStep, payload: dict) -> dict:
    """Execute a single action step and return a result dict."""
    if step.action_type == "http_request":
        url = step.meta.get("url")
        if not url:
            return {"ok": False, "detail": "http_request action missing meta.url"}
        method = step.meta.get("method", "POST").upper()
        try:
            response = httpx.request(
                method, url, json=payload, timeout=settings.HTTP_ACTION_TIMEOUT_SECONDS
            )
            return {"ok": response.is_success, "status_code": response.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "detail": f"http error: {exc}"}

    if step.action_type in ("viber", "email"):
        # Outbound channel integrations land in a later milestone; for now we
        # log the send so runs are observable end-to-end. See DECISIONS.md.
        logger.info(
            "[%s] would send template=%s payload_keys=%s",
            step.action_type,
            step.meta.get("template"),
            sorted(payload.keys()),
        )
        return {"ok": True, "detail": f"{step.action_type} send logged (stub)"}

    return {"ok": False, "detail": f"unknown action_type: {step.action_type}"}


def execute_workflow(raw_steps: list[dict], payload: dict) -> list[dict]:
    """Run a workflow's steps against a trigger payload.

    Returns one result dict per processed step:
      {"step": n, "type": ..., "result": ...}
    Execution stops at the first false condition.
    """
    steps = parse_steps(raw_steps)
    results: list[dict] = []

    for step in steps:
        if step.type == "trigger":
            results.append({"step": step.step, "type": "trigger", "result": "fired"})
            continue

        if step.type == "condition":
            passed = evaluate_condition(step, payload)
            results.append({"step": step.step, "type": "condition", "result": passed})
            if not passed:
                logger.info("workflow stopped: condition at step %s is false", step.step)
                break
            continue

        # action
        outcome = execute_action(step, payload)
        results.append({"step": step.step, "type": "action", "result": outcome})

    return results
