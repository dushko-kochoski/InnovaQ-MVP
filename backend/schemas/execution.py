from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str
    results: list[Any]
    triggered_at: datetime
