"""Pydantic models for scene perception data."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class DetectedObject(BaseModel):
    id: str
    name: str
    position: Literal["far-left", "center-left", "center", "center-right", "far-right"]
    estimated_size: Literal["tiny", "small", "medium", "large"]
    color: str
    material_guess: str
    graspable: bool
    confidence: float = Field(ge=0.0, le=1.0)


class SceneDescription(BaseModel):
    objects: list[DetectedObject]
    scene_description: str
    workspace_clear: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
