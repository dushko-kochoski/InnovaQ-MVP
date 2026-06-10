from pydantic import BaseModel, ConfigDict

from backend.schemas.workflow import Niche, WorkflowStep


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: str
    slug: str
    name: str
    niche: Niche
    description: str
    steps: list[WorkflowStep]
