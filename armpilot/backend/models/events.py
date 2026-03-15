"""
WebSocket event schemas — all event types flowing between server and client.

Server → Client:
  camera_frame       : Raw camera frames (~2 FPS)
  perception_result  : VLM scene analysis
  reasoning_step     : Agent reasoning progress
  tavily_result      : Tavily search results
  action_plan        : Generated action plan
  execution_update   : Arm movement progress
  homer_result       : Toloka HomER demo matches
  security_eval      : Toloka security eval progress/results
  error              : Error notifications

Client → Server:
  command            : User voice/text command
  approve            : Approve pending action
  reject             : Reject pending action
  capture_scene      : Trigger manual perception
  security_eval      : Trigger security eval
  homer_search       : Search HomER demos
"""

from pydantic import BaseModel
from typing import Literal


# ── Client → Server ──────────────────────────────────────

class CommandEvent(BaseModel):
    type: Literal["command"]
    text: str

class ApproveEvent(BaseModel):
    type: Literal["approve"]
    action_id: str

class RejectEvent(BaseModel):
    type: Literal["reject"]
    action_id: str

class CaptureSceneEvent(BaseModel):
    type: Literal["capture_scene"]

class SecurityEvalTriggerEvent(BaseModel):
    type: Literal["security_eval"]

class HomerSearchEvent(BaseModel):
    type: Literal["homer_search"]
    query: str


# ── Server → Client ──────────────────────────────────────

class CameraFrameEvent(BaseModel):
    type: Literal["camera_frame"]
    data: dict  # {frame_b64: str, width: int, height: int}
    timestamp: str

class PerceptionResultEvent(BaseModel):
    type: Literal["perception_result"]
    data: dict  # SceneDescription.model_dump()
    timestamp: str
    latency_ms: int = 0

class ReasoningStepEvent(BaseModel):
    type: Literal["reasoning_step"]
    data: dict  # {step: str, detail: str, tavily_query?: str}
    timestamp: str
    # step values:
    # "connected" | "perceiving" | "searching" | "planning" | "awaiting_approval" | "executing" | "completed"

class TavilyResultEvent(BaseModel):
    type: Literal["tavily_result"]
    data: dict  # {query: str, results: [{title, content, url, score}]}
    timestamp: str

class ActionPlanEvent(BaseModel):
    type: Literal["action_plan"]
    data: dict  # ActionPlan.model_dump()
    timestamp: str

class ExecutionUpdateEvent(BaseModel):
    type: Literal["execution_update"]
    data: dict  # {current_step, total_steps, joint_positions, gripper_state, status}
    timestamp: str
    # status values: "executing" | "completed" | "failed"

class HomerResultEvent(BaseModel):
    type: Literal["homer_result"]
    data: dict  # {demos: str|list, source: str, query?: str}
    timestamp: str

class SecurityEvalEvent(BaseModel):
    type: Literal["security_eval"]
    data: dict  # {status, total, completed, passed?, failed?, score?, results?, message}
    timestamp: str

class ErrorEvent(BaseModel):
    type: Literal["error"]
    data: dict  # {message: str, recoverable: bool}
    timestamp: str
