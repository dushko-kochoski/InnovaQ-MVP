from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Niche = Literal["accounting", "trade", "real_estate", "logistics", "healthcare"]
WorkflowStatus = Literal["active", "paused", "draft"]

TRIGGER_ACTION_TYPES = {"webhook_receive", "schedule", "http_poll"}
ACTION_ACTION_TYPES = {"http_request", "viber", "email"}
CONDITION_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains"}


class WorkflowStep(BaseModel):
    """One step of a workflow: trigger, condition, or action.

    Field requirements depend on `type`, enforced in the validator below.
    """

    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1)
    type: Literal["trigger", "condition", "action"]
    action_type: str | None = None
    field: str | None = None
    operator: str | None = None
    value: Any | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_by_type(self) -> "WorkflowStep":
        if self.type == "trigger":
            if self.action_type not in TRIGGER_ACTION_TYPES:
                raise ValueError(
                    f"trigger step requires action_type in {sorted(TRIGGER_ACTION_TYPES)}"
                )
        elif self.type == "condition":
            if not self.field:
                raise ValueError("condition step requires 'field'")
            if self.operator not in CONDITION_OPERATORS:
                raise ValueError(
                    f"condition step requires operator in {sorted(CONDITION_OPERATORS)}"
                )
        elif self.type == "action":
            if self.action_type not in ACTION_ACTION_TYPES:
                raise ValueError(
                    f"action step requires action_type in {sorted(ACTION_ACTION_TYPES)}"
                )
        return self


def validate_steps_order(steps: list[WorkflowStep]) -> list[WorkflowStep]:
    """Shared rule: non-empty, first step is a trigger, step numbers are unique."""
    if not steps:
        raise ValueError("workflow must contain at least one step")
    ordered = sorted(steps, key=lambda s: s.step)
    if ordered[0].type != "trigger":
        raise ValueError("first step must be a trigger")
    numbers = [s.step for s in ordered]
    if len(set(numbers)) != len(numbers):
        raise ValueError("step numbers must be unique")
    return ordered


class WorkflowCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    niche: Niche
    status: WorkflowStatus = "draft"
    steps: list[WorkflowStep]

    @model_validator(mode="after")
    def _check_steps(self) -> "WorkflowCreateRequest":
        self.steps = validate_steps_order(self.steps)
        return self


class WorkflowUpdateRequest(BaseModel):
    """All fields optional — PUT applies only what is provided."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    niche: Niche | None = None
    status: WorkflowStatus | None = None
    steps: list[WorkflowStep] | None = None

    @model_validator(mode="after")
    def _check_steps(self) -> "WorkflowUpdateRequest":
        if self.steps is not None:
            self.steps = validate_steps_order(self.steps)
        return self


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_id: str
    user_id: str
    name: str
    niche: Niche
    status: WorkflowStatus
    route_key: str
    steps: list[WorkflowStep]
    created_at: datetime
    updated_at: datetime
