"""Validates and parses raw workflow step JSON into typed WorkflowStep objects."""

from pydantic import ValidationError

from backend.schemas.workflow import WorkflowStep, validate_steps_order


class WorkflowParseError(Exception):
    """Raised when stored workflow JSON is invalid."""


def parse_steps(raw_steps: list[dict]) -> list[WorkflowStep]:
    """Parse raw step dicts into validated WorkflowStep objects, sorted by step number.

    Raises WorkflowParseError on any structural or semantic problem.
    """
    if not isinstance(raw_steps, list):
        raise WorkflowParseError("steps must be a list")
    try:
        steps = [WorkflowStep.model_validate(item) for item in raw_steps]
        return validate_steps_order(steps)
    except (ValidationError, ValueError) as exc:
        raise WorkflowParseError(str(exc)) from exc
