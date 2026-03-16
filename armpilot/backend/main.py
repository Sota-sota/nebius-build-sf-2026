import asyncio
import json
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ArmPilot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

clients: set[WebSocket] = set()
pending_approval = None
perception_agent = None
camera_task = None

# Fallback scene when camera is unavailable
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


# ── Lifecycle ────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global perception_agent, camera_task
    from agents.perception import PerceptionAgent
    perception_agent = PerceptionAgent()

    # Start camera streaming if camera is available
    if perception_agent.has_camera:
        camera_task = asyncio.create_task(perception_agent.stream_camera(broadcast))
        print("[Startup] Camera streaming started")
    else:
        print("[Startup] No camera detected — using mock scene data")


@app.on_event("shutdown")
async def shutdown():
    global camera_task
    if perception_agent:
        perception_agent.stop_stream()
        perception_agent.release()
    if camera_task:
        camera_task.cancel()


# ── REST Endpoints ───────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    import os
    from config import ARM_PORT
    return {
        "arm_connected": os.path.exists(ARM_PORT),
        "camera_ready": perception_agent.has_camera if perception_agent else False,
        "apis_ready": True,
        "clients": len(clients),
    }


@app.post("/api/broadcast")
async def broadcast_event(event: dict):
    """Relay an event to all connected WebSocket clients."""
    await broadcast(event)
    return {"ok": True}


@app.get("/api/homer")
async def homer_dataset():
    """Return Toloka HomER dataset metadata."""
    from tools.toloka_homer import load_homer_dataset
    data = await load_homer_dataset()
    return {"dataset": "toloka/HomER", "count": len(data), "records": data}


@app.get("/api/homer/search")
async def homer_search(q: str = "pick up", max_results: int = 3):
    """Find relevant HomER demos for a query."""
    from tools.toloka_homer import find_relevant_demos
    demos = await find_relevant_demos(q, q.split(), max_results)
    return {"query": q, "results": demos}


@app.post("/api/security-eval")
async def security_eval_endpoint():
    """Run Toloka security evaluation against the reasoning agent."""
    from tools.toloka_security import run_security_eval
    results = await run_security_eval(broadcast)
    return results


# ── WebSocket ────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    await broadcast({
        "type": "reasoning_step",
        "data": {"step": "connected", "detail": "Client connected"},
    })
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
                asyncio.create_task(capture_scene())
            elif t == "security_eval":
                asyncio.create_task(run_security_eval_ws())
            elif t == "homer_search":
                asyncio.create_task(run_homer_search(msg.get("query", "")))
    except WebSocketDisconnect:
        clients.discard(websocket)


# ── Pipeline ─────────────────────────────────────────────

async def get_scene() -> dict:
    """Get the current scene — from perception agent if camera available, else mock."""
    if perception_agent and perception_agent.has_camera:
        scene = await perception_agent.capture_and_analyze(broadcast)
        if scene:
            return scene.model_dump(mode="json")
    # Broadcast mock scene so frontend still populates
    await broadcast({"type": "perception_result", "data": MOCK_SCENE})
    return MOCK_SCENE


async def capture_scene():
    """Manual scene capture triggered by frontend."""
    await get_scene()


async def run_pipeline(command: str):
    global pending_approval
    from agents.reasoning import ReasoningAgent
    from agents.planner import ActionPlanner
    from agents.executor import get_executor

    try:
        # Step 1: Perception
        scene = await get_scene()

        # Step 2: Reasoning + Tavily
        agent = ReasoningAgent()
        plan = await agent.reason(command, scene, broadcast)

        # Step 3: Execute or await approval
        if not plan.requires_approval:
            planner = ActionPlanner()
            waypoints = planner.plan_to_waypoints(plan)
            executor = get_executor()
            await executor.execute(waypoints, plan, broadcast)
        else:
            pending_approval = plan
    except Exception as e:
        await broadcast({
            "type": "error",
            "data": {"message": str(e), "recoverable": True},
        })


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
    await broadcast({
        "type": "error",
        "data": {"message": "Action rejected by user.", "recoverable": True},
    })


async def run_security_eval_ws():
    """Run Toloka security eval triggered via WebSocket."""
    from tools.toloka_security import run_security_eval
    await run_security_eval(broadcast)


async def run_homer_search(query: str):
    """Search HomER dataset triggered via WebSocket."""
    from tools.toloka_homer import find_relevant_demos
    demos = await find_relevant_demos(query, query.split(), 3)
    await broadcast({
        "type": "homer_result",
        "data": {
            "demos": [
                f"[{d['task_category']}] {d['scenario']}: {d['description']}"
                for d in demos
            ],
            "source": "toloka/HomER",
            "query": query,
        },
    })
