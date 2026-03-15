"""
WebSocket event schemas — Person B と共有するコントラクト

Server → Client:
  camera_frame       : カメラ映像 (2FPS)
  perception_result  : VLM解析結果
  reasoning_step     : 推論の各ステップ
  tavily_result      : Tavily検索結果
  action_plan        : 生成されたアクションプラン
  execution_update   : アーム動作の進捗
  error              : エラー通知

Client → Server:
  command            : ユーザーコマンド
  approve            : アクション承認
  reject             : アクション拒否
  capture_scene      : 知覚トリガー
"""

from pydantic import BaseModel
from typing import Literal, Any


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


# ── Server → Client ──────────────────────────────────────

class CameraFrameEvent(BaseModel):
    type: Literal["camera_frame"]
    data: dict  # {frame_b64: str, width: int, height: int}
    timestamp: str

class PerceptionResultEvent(BaseModel):
    type: Literal["perception_result"]
    data: dict  # SceneDescription
    timestamp: str
    latency_ms: int = 0

class ReasoningStepEvent(BaseModel):
    type: Literal["reasoning_step"]
    data: dict  # {step: str, detail: str, tavily_query?: str}
    timestamp: str

    # step values:
    # "connected" | "searching" | "planning" | "awaiting_approval" | "executing"

class TavilyResultEvent(BaseModel):
    type: Literal["tavily_result"]
    data: dict  # {query: str, results: [{title, content, url}]}
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

class ErrorEvent(BaseModel):
    type: Literal["error"]
    data: dict  # {message: str, recoverable: bool}
    timestamp: str
