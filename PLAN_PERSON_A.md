# ArmPilot — 30分スプリント (ロボット接続まで)

**ゴール**: コマンド送信 → Nebius推論 → SO101アームが動く、をこの30分で完成させる。
カメラ・フロントエンドは後回し。まずアームを動かす。

---

## チェックリスト (30分)

### Min 0–5: 環境セットアップ
- [x] ディレクトリ作成 + パッケージインストール
- [x] `.env` 作成 (APIキー記入)
- [x] `config.py` 作成
- [x] Nebius API 疎通確認 (`scripts/test_nebius.py`)
- [x] Tavily API 疎通確認 (`scripts/test_tavily.py`)

### Min 5–10: FastAPI + WebSocket
- [x] `main.py` 作成 (FastAPI + `/ws` + `broadcast()`)
- [x] `uvicorn` 起動確認

### Min 10–15: 推論 + Tavily
- [x] `models/action.py` 作成 (ActionStep, ActionPlan)
- [x] `tools/tavily_search.py` 作成
- [x] `agents/reasoning.py` 作成
- [x] `wscat` でコマンド送信 → ActionPlan が返ってくることを確認

### Min 15–20: アーム校正
- [x] SO101 USB接続確認 (`/dev/cu.usbmodem5AE70495381`)
- [x] `lerobot-calibrate` 実行 (calibration saved to ~/.cache/huggingface/lerobot/...)
- [x] `config.py` の `POSITION_MAP` を実測値で更新

### Min 20–28: プランナー + エグゼキューター → アーム動作
- [x] `agents/planner.py` 作成 (ActionPlan → waypoints)
- [x] `agents/executor.py` 作成 (LeRobot → SO101)
- [x] `main.py` に `execute_plan()` 接続
- [x] **アームが実際に動くことを確認**

### Min 28–30: 動作確認
- [x] "pick up the red cup" コマンド → アーム動作をエンドツーエンドで確認
- [ ] Person B に `models/events.py` の WS スキーマを共有

---

## 実装コード (コピペして使う)

### Step 1: セットアップ

```bash
mkdir -p armpilot/backend/agents armpilot/backend/tools armpilot/backend/models armpilot/scripts
cd armpilot/backend
uv init
uv add fastapi uvicorn websockets openai tavily-python pydantic python-dotenv numpy torch lerobot
```

`.env`:
```env
NEBIUS_API_KEY=your_key
NEBIUS_MODEL=meta-llama/Llama-3.3-70B-Instruct
TAVILY_API_KEY=your_key
OPENROUTER_API_KEY=your_key
OPENROUTER_VISION_MODEL=qwen/qwen2.5-vl-72b-instruct
ARM_PORT=/dev/ttyACM0
ARM_ID=armpilot_follower
CAMERA_INDEX=0
BACKEND_PORT=8000
```

### Step 2: `backend/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

NEBIUS_API_KEY    = os.getenv("NEBIUS_API_KEY")
NEBIUS_MODEL      = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
TAVILY_API_KEY    = os.getenv("TAVILY_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ARM_PORT          = os.getenv("ARM_PORT", "/dev/ttyACM0")
ARM_ID            = os.getenv("ARM_ID", "armpilot_follower")
CAMERA_INDEX      = int(os.getenv("CAMERA_INDEX", "0"))
BACKEND_PORT      = int(os.getenv("BACKEND_PORT", "8000"))

# ← アーム校正後にこの値を実測値に更新する
POSITION_MAP = {
    "home":         [0.0,   0.0,   0.0,   0.0,   0.0,   0.0],
    "far-left":     [-1.2, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-left":  [-0.6, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center":       [0.0,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-right": [0.6,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "far-right":    [1.2,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "above":        [0.0,  -0.2,   0.3,   0.0,   0.0,   0.0],
}

GRIPPER_OPEN           = 0.0
GRIPPER_CLOSED_GENTLE  = 0.5
GRIPPER_CLOSED_NORMAL  = 0.75
GRIPPER_CLOSED_FIRM    = 1.0

JOINT_LIMITS = {
    "min": [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0],
    "max": [ 2.0,  2.0,  2.0,  2.0,  2.0, 1.0],
}
```

### Step 3: `backend/main.py`

```python
import asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

clients: set[WebSocket] = set()
pending_approval = None

async def broadcast(event: dict):
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
    msg = json.dumps(event)
    for ws in list(clients):
        try:
            await ws.send_text(msg)
        except Exception:
            clients.discard(ws)

@app.get("/")
def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg["type"] == "command":
                asyncio.create_task(run_pipeline(msg["text"]))
            elif msg["type"] == "approve":
                asyncio.create_task(approve_pending(msg["action_id"]))
            elif msg["type"] == "reject":
                asyncio.create_task(reject_pending(msg["action_id"]))
    except WebSocketDisconnect:
        clients.discard(websocket)

async def run_pipeline(command: str):
    from agents.reasoning import ReasoningAgent
    from agents.planner import ActionPlanner
    from agents.executor import get_executor
    global pending_approval

    # ハードコードシーン (知覚パイプラインは後で追加)
    scene = {
        "objects": [{"id": "obj_1", "name": "red cup", "position": "center",
                     "estimated_size": "small", "color": "red",
                     "material_guess": "ceramic", "graspable": True, "confidence": 0.9}],
        "scene_description": "A red cup on the workspace",
        "workspace_clear": True,
    }

    agent = ReasoningAgent()
    plan = await agent.reason(command, scene, broadcast)

    if not plan.requires_approval:
        planner = ActionPlanner()
        waypoints = planner.plan_to_waypoints(plan)
        executor = get_executor()
        await executor.execute(waypoints, plan, broadcast)
    else:
        pending_approval = plan

async def approve_pending(action_id: str):
    from agents.planner import ActionPlanner
    from agents.executor import get_executor
    global pending_approval
    if pending_approval and pending_approval.action_id == action_id:
        planner = ActionPlanner()
        waypoints = planner.plan_to_waypoints(pending_approval)
        executor = get_executor()
        await executor.execute(waypoints, pending_approval, broadcast)
        pending_approval = None

async def reject_pending(action_id: str):
    global pending_approval
    pending_approval = None
    await broadcast({"type": "error", "data": {"message": "Action rejected", "recoverable": True}})
```

### Step 4: `backend/models/action.py`

```python
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
```

### Step 5: `backend/tools/tavily_search.py`

```python
import asyncio
from tavily import TavilyClient
from config import TAVILY_API_KEY

class TavilySearchTool:
    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)
        self.cache: dict = {}

    async def search(self, query: str) -> list[dict]:
        if query in self.cache:
            return self.cache[query]
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(self.client.search, query, search_depth="basic", max_results=3),
                timeout=5.0
            )
            formatted = [{"title": r["title"], "content": r["content"][:200], "url": r["url"]}
                         for r in results.get("results", [])]
            self.cache[query] = formatted
            return formatted
        except Exception:
            return []

    async def search_for_command(self, objects: list[str], task: str, broadcast_fn) -> str:
        queries = [
            f"{objects[0] if objects else 'object'} weight material properties",
            f"robotic arm safe grip handling",
            f"robot arm {task} best practice",
        ]
        context_parts = []
        for q in queries[:3]:
            results = await self.search(q)
            await broadcast_fn({"type": "tavily_result", "data": {"query": q, "results": results}})
            for r in results:
                context_parts.append(f"[{r['title']}] {r['content']}")
        return "\n".join(context_parts) or "No web search results. Proceed with caution."
```

### Step 6: `backend/agents/reasoning.py`

```python
import json
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_MODEL
from models.action import ActionPlan, ActionStep
from tools.tavily_search import TavilySearchTool

SYSTEM_PROMPT = """You are ArmPilot controlling a 6-DOF SO101 robotic arm.
Positions: far-left, center-left, center, center-right, far-right, above.
Actions: move_to, grasp (force: gentle/normal/firm), release, pause.
Risk: low=common objects, medium=fragile, high=dangerous/uncertain.
requires_approval=true if risk != low.
Return ONLY valid JSON, no markdown:
{"reasoning":"...","tavily_queries_used":[],"knowledge_summary":"...","risk_level":"low","risk_justification":"...","actions":[{"step":1,"action":"move_to","target":"center","description":"..."}],"requires_approval":false}"""

class ReasoningAgent:
    def __init__(self):
        self.client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1", api_key=NEBIUS_API_KEY)
        self.tavily = TavilySearchTool()

    async def reason(self, command: str, scene: dict, broadcast_fn) -> ActionPlan:
        await broadcast_fn({"type": "reasoning_step", "data": {"step": "searching", "detail": "Running Tavily searches..."}})
        objects = [o["name"] for o in scene.get("objects", [])]
        context = await self.tavily.search_for_command(objects, command, broadcast_fn)

        await broadcast_fn({"type": "reasoning_step", "data": {"step": "planning", "detail": "Generating action plan..."}})
        user_msg = f"Command: {command}\nScene: {json.dumps(scene)}\nWeb knowledge:\n{context}"

        import asyncio
        response = await asyncio.to_thread(
            lambda: self.client.chat.completions.create(
                model=NEBIUS_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_msg}],
                temperature=0.3,
                max_tokens=1500,
            )
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        plan = ActionPlan(**data)

        await broadcast_fn({"type": "action_plan", "data": plan.model_dump()})
        if plan.requires_approval:
            await broadcast_fn({"type": "reasoning_step", "data": {"step": "awaiting_approval", "detail": f"Risk={plan.risk_level}. Waiting for human approval."}})
        return plan
```

### Step 7: `backend/agents/planner.py`

```python
from config import POSITION_MAP, GRIPPER_OPEN, GRIPPER_CLOSED_GENTLE, GRIPPER_CLOSED_NORMAL, GRIPPER_CLOSED_FIRM, JOINT_LIMITS
from models.action import ActionPlan

GRIPPER_FORCE_MAP = {"gentle": GRIPPER_CLOSED_GENTLE, "normal": GRIPPER_CLOSED_NORMAL, "firm": GRIPPER_CLOSED_FIRM}

class ActionPlanner:
    def __init__(self):
        self.current = [0.0] * 6

    def plan_to_waypoints(self, plan: ActionPlan) -> list:
        waypoints = []
        for step in plan.actions:
            if step.action == "move_to":
                pos = list(POSITION_MAP.get(step.target, POSITION_MAP["center"]))
                pos[5] = self.current[5]  # keep current gripper
                self._validate(pos)
                waypoints.append(pos)
            elif step.action == "grasp":
                pos = list(self.current)
                pos[5] = GRIPPER_FORCE_MAP.get(step.force or "normal", GRIPPER_CLOSED_NORMAL)
                waypoints.append(pos)
            elif step.action == "release":
                pos = list(self.current)
                pos[5] = GRIPPER_OPEN
                waypoints.append(pos)
            elif step.action == "pause":
                waypoints.append(None)
        return waypoints

    def _validate(self, pos: list):
        for i, v in enumerate(pos):
            if not (JOINT_LIMITS["min"][i] <= v <= JOINT_LIMITS["max"][i]):
                raise ValueError(f"Joint {i} value {v} out of limits")
```

### Step 8: `backend/agents/executor.py`

```python
import asyncio, os, torch
from config import ARM_PORT, ARM_ID, POSITION_MAP
from models.action import ActionPlan

STEP_DELAY_S = 0.3
INTERPOLATION_STEPS = 5

def interpolate(start, end, steps):
    return [[start[j] + (end[j] - start[j]) * i / steps for j in range(len(start))]
            for i in range(1, steps + 1)]

class ArmExecutor:
    def __init__(self):
        from lerobot.common.robot_devices.robots.factory import make_robot
        self.robot = make_robot("so101_follower", port=ARM_PORT, id=ARM_ID)
        self.current = [0.0] * 6

    async def execute(self, waypoints: list, plan: ActionPlan, broadcast_fn):
        await broadcast_fn({"type": "reasoning_step", "data": {"step": "executing", "detail": "Executing on arm..."}})
        total = len([w for w in waypoints if w is not None])
        done = 0
        for wp in waypoints:
            if wp is None:
                await asyncio.sleep(1.0)
                continue
            for interp in interpolate(self.current, wp, INTERPOLATION_STEPS):
                self.robot.send_action(torch.tensor(interp, dtype=torch.float32))
                await asyncio.sleep(STEP_DELAY_S / INTERPOLATION_STEPS)
            self.current = wp
            done += 1
            await broadcast_fn({"type": "execution_update", "data": {
                "current_step": done, "total_steps": total,
                "joint_positions": self.current[:5], "gripper_state": "closed" if self.current[5] > 0.1 else "open",
                "status": "executing"
            }})
        await broadcast_fn({"type": "execution_update", "data": {"status": "completed", "current_step": total, "total_steps": total, "joint_positions": self.current[:5], "gripper_state": "open"}})

class DummyExecutor:
    """アーム未接続時のフォールバック"""
    def __init__(self):
        self.current = [0.0] * 6

    async def execute(self, waypoints: list, plan: ActionPlan, broadcast_fn):
        await broadcast_fn({"type": "reasoning_step", "data": {"step": "executing", "detail": "[DummyExecutor] Simulating arm..."}})
        for i, wp in enumerate([w for w in waypoints if w is not None]):
            await asyncio.sleep(0.5)
            await broadcast_fn({"type": "execution_update", "data": {
                "current_step": i + 1, "total_steps": len(waypoints),
                "joint_positions": wp[:5], "gripper_state": "closed" if wp[5] > 0.1 else "open",
                "status": "executing"
            }})
        await broadcast_fn({"type": "execution_update", "data": {"status": "completed"}})

def get_executor():
    if os.path.exists(ARM_PORT):
        return ArmExecutor()
    print(f"[WARNING] {ARM_PORT} not found. Using DummyExecutor.")
    return DummyExecutor()
```

### Step 9: API疎通テスト

`scripts/test_nebius.py`:
```python
import sys; sys.path.insert(0, "../backend")
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_MODEL
client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1", api_key=NEBIUS_API_KEY)
r = client.chat.completions.create(model=NEBIUS_MODEL, messages=[{"role": "user", "content": "Say OK"}], max_tokens=10)
print("Nebius OK:", r.choices[0].message.content)
```

`scripts/test_tavily.py`:
```python
import sys; sys.path.insert(0, "../backend")
from tavily import TavilyClient
from config import TAVILY_API_KEY
c = TavilyClient(api_key=TAVILY_API_KEY)
r = c.search("ceramic mug weight", search_depth="basic", max_results=2)
print("Tavily OK:", [x["title"] for x in r["results"]])
```

### Step 10: 起動 + テスト

```bash
# バックエンド起動
cd armpilot/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 別ターミナルでWS接続テスト
npx wscat -c ws://localhost:8000/ws

# コマンド送信 (wscat 内で)
{"type": "command", "text": "pick up the red cup and move it to the left"}
```

---

## フォールバック (詰まったとき)

| 問題 | 即時対処 |
|------|----------|
| アーム未接続 | `DummyExecutor` が自動で使われる。そのまま推論テスト続行 |
| Nebius API エラー | `scripts/test_nebius.py` でキー確認 |
| Tavily タイムアウト | `tools/tavily_search.py` のタイムアウトを 10s に延ばす |
| JSON パースエラー | LLM レスポンスを print してプロンプト修正 |
| アーム校正未完了 | `POSITION_MAP` はプレースホルダーのままで OK、後で更新 |

---

## Person B への共有 (Min 15 までに)

`backend/models/events.py` を作って渡す。最低限これだけあれば Person B が frontend を作れる:

```python
# WebSocket イベント一覧 (Person B 用)
# Server → Client:
# {"type": "camera_frame",       "data": {"frame_b64": str, "width": int, "height": int}}
# {"type": "perception_result",  "data": SceneDescription}
# {"type": "reasoning_step",     "data": {"step": str, "detail": str}, "timestamp": str}
# {"type": "tavily_result",      "data": {"query": str, "results": [...]}, "timestamp": str}
# {"type": "action_plan",        "data": ActionPlan, "timestamp": str}
# {"type": "execution_update",   "data": {"current_step": int, "total_steps": int, "joint_positions": list, "gripper_state": str, "status": str}}
# {"type": "error",              "data": {"message": str, "recoverable": bool}}

# Client → Server:
# {"type": "command",       "text": str}
# {"type": "approve",       "action_id": str}
# {"type": "reject",        "action_id": str}
# {"type": "capture_scene"}
```
