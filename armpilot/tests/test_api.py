"""
FastAPI endpoint tests: GET /, GET /api/status, WebSocket /ws.
All agents mocked — no LLM, no robot, no network calls.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from models.action import ActionPlan, ActionStep


MOCK_PLAN_LOW = ActionPlan(
    reasoning="test",
    risk_level="low",
    risk_justification="safe",
    actions=[
        ActionStep(step=1, action="move_to", target="center", description="move"),
        ActionStep(step=2, action="grasp", force="gentle", description="grasp"),
    ],
    requires_approval=False,
)

MOCK_PLAN_HIGH = ActionPlan(
    reasoning="dangerous",
    risk_level="high",
    risk_justification="sharp",
    actions=[
        ActionStep(step=1, action="move_to", target="center", description="approach"),
    ],
    requires_approval=True,
)


@pytest.fixture
def client():
    import main as m
    return TestClient(m.app, raise_server_exceptions=True)


# ── GET / ──────────────────────────────────────────────────────────────────


def test_health_returns_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── GET /api/status ────────────────────────────────────────────────────────


def test_status_has_required_fields(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "arm_connected" in body
    assert "camera_ready" in body
    assert "apis_ready" in body
    assert "clients" in body


def test_status_arm_not_connected_when_no_port(client, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda _: False)
    r = client.get("/api/status")
    assert r.json()["arm_connected"] is False


# ── WebSocket /ws — connection ─────────────────────────────────────────────


def test_ws_connect_broadcasts_connected_event(client):
    with client.websocket_connect("/ws") as ws:
        data = json.loads(ws.receive_text())
        assert data["type"] == "reasoning_step"
        assert data["data"]["step"] == "connected"


# ── WebSocket /ws — capture_scene ─────────────────────────────────────────


def test_ws_capture_scene_returns_perception_result(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_text()  # consume connection event
        ws.send_text(json.dumps({"type": "capture_scene"}))
        data = json.loads(ws.receive_text())
        assert data["type"] == "perception_result"
        assert "objects" in data["data"]


# ── WebSocket /ws — command dispatches task (tested via run_pipeline) ──────
# NOTE: WS command handling calls asyncio.create_task(run_pipeline(...)) which
# runs asynchronously. Pipeline behavior is covered by test_main_pipeline.py.
# Here we only verify the WS message is accepted without error.


def test_ws_command_accepted_without_error(client):
    """WS accepts a command message without raising."""
    with patch("agents.reasoning.ReasoningAgent.reason", new_callable=AsyncMock, return_value=MOCK_PLAN_LOW), \
         patch("agents.executor.get_executor", return_value=MagicMock(execute=AsyncMock(), current=[0.0]*6)), \
         patch("config.USE_SMOLVLA", False):
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()  # connected event
            # Should not raise
            ws.send_text(json.dumps({"type": "command", "text": "pick up the red cup"}))


def test_ws_unknown_message_type_ignored(client):
    """Unknown WS message types are silently ignored."""
    with client.websocket_connect("/ws") as ws:
        ws.receive_text()  # connected event
        ws.send_text(json.dumps({"type": "unknown_type", "data": "x"}))


# ── broadcast ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_adds_timestamp():
    import main as m

    received = []

    class FakeWS:
        async def send_text(self, text):
            received.append(json.loads(text))

    m.clients.clear()
    m.clients.add(FakeWS())

    await m.broadcast({"type": "test_event", "data": {}})
    m.clients.clear()

    assert len(received) == 1
    assert "timestamp" in received[0]


@pytest.mark.asyncio
async def test_broadcast_does_not_override_existing_timestamp():
    import main as m

    received = []

    class FakeWS:
        async def send_text(self, text):
            received.append(json.loads(text))

    m.clients.clear()
    m.clients.add(FakeWS())

    await m.broadcast({"type": "test", "timestamp": "fixed-ts"})
    m.clients.clear()

    assert received[0]["timestamp"] == "fixed-ts"


@pytest.mark.asyncio
async def test_broadcast_removes_failed_clients():
    import main as m

    class BrokenWS:
        async def send_text(self, text):
            raise RuntimeError("disconnected")

    m.clients.clear()
    m.clients.add(BrokenWS())

    await m.broadcast({"type": "test"})

    assert len(m.clients) == 0
