from pydantic import BaseModel, Field
from typing import Literal
import uuid


class ActionStep(BaseModel):
    step: int
    action: Literal["move_to", "grasp", "release", "pause"]
    target: str | None = None
    force: Literal["gentle", "normal", "firm"] | None = None
    description: str


class ActionPlan(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reasoning: str
    tavily_queries_used: list[str] = []
    knowledge_summary: str = ""
    risk_level: Literal["low", "medium", "high"]
    risk_justification: str
    actions: list[ActionStep]
    requires_approval: bool
