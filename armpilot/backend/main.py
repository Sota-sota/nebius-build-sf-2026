import asyncio
import json
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

clients: set[WebSocket] = set()
pending_approval = None

# ハードコードシーン (知覚パイプラインは後で追加)
MOCK_SCENE = {
    "objects": [
        {
            "id": "obj_1",
            "name": "red cup",
            "position": "center",
            "estimated_size": "small",
            "color": "red",
            "material_guess": "ceramic",
            "graspable": True,
            "confidence": 0.9,
        }
    ],
    "scene_description": "A red ceramic cup on the workspace",
    "workspace_clear": True,
}


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


@app.get("/api/status")
def status():
    import os
    from config import ARM_PORT
    return {
        "arm_connected": os.path.exists(ARM_PORT),
        "camera_ready": False,
        "apis_ready": True,
        "clients": len(clients),
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    await broadcast({"type": "reasoning_step", "data": {"step": "connected", "detail": "Client connected"}})
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            t = msg.get("type")
            if t == "command":
                asyncio.create_task(run_pipeline(msg["text"]))
            elif t == "approve":
                asyncio.create_task(approve_pending(msg["action_id"]))
            elif t == "reject":
                asyncio.create_task(reject_pending(msg["action_id"]))
            elif t == "capture_scene":
                await broadcast({"type": "perception_result", "data": MOCK_SCENE})
    except WebSocketDisconnect:
        clients.discard(websocket)


async def run_pipeline(command: str):
    global pending_approval
    from agents.reasoning import ReasoningAgent
    from agents.planner import ActionPlanner
    from agents.executor import get_executor

    try:
        agent = ReasoningAgent()
        plan = await agent.reason(command, MOCK_SCENE, broadcast)

        if not plan.requires_approval:
            planner = ActionPlanner()
            waypoints = planner.plan_to_waypoints(plan)
            executor = get_executor()
            await executor.execute(waypoints, plan, broadcast)
        else:
            pending_approval = plan
    except Exception as e:
        await broadcast({"type": "error", "data": {"message": str(e), "recoverable": True}})


async def approve_pending(action_id: str):
    global pending_approval
    if pending_approval and pending_approval.action_id == action_id:
        from agents.planner import ActionPlanner
        from agents.executor import get_executor
        planner = ActionPlanner()
        waypoints = planner.plan_to_waypoints(pending_approval)
        executor = get_executor()
        await executor.execute(waypoints, pending_approval, broadcast)
        pending_approval = None


async def reject_pending(action_id: str):
    global pending_approval
    pending_approval = None
    await broadcast({"type": "error", "data": {"message": "Action rejected by user.", "recoverable": True}})
