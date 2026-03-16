"""
Integration tests for SmolVLA HTTP path.
Starts dummy_smolvla_server in a background thread (real TCP), no mocks.

Run: pytest -m integration tests/test_smolvla_integration.py -v
"""
import socket
import threading
import time
import sys
import os

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def dummy_server_url():
    """Dummy SmolVLA サーバーを別スレッドで起動し URL を返す"""
    import uvicorn
    from dummy_smolvla_server import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # 起動待機 (最大 3 秒)
    for _ in range(60):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


# ── Group A: Dummy サーバー直接テスト ──────────────────────────────────

@pytest.mark.integration
def test_health_endpoint(dummy_server_url):
    r = httpx.get(f"{dummy_server_url}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model" in body


@pytest.mark.integration
def test_predict_returns_valid_schema(dummy_server_url):
    payload = {
        "instruction": "pick up the red cup",
        "joint_state": [0.0] * 6,
        "image_b64": None,
    }
    r = httpx.post(f"{dummy_server_url}/predict", json=payload)
    assert r.status_code == 200
    chunk = r.json()["actions"]
    assert len(chunk) == 10
    assert all(len(step) == 6 for step in chunk)


@pytest.mark.integration
def test_predict_chunk_within_limits(dummy_server_url):
    MINS = [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0]
    MAXS = [ 2.0,  2.0,  2.0,  2.0,  2.0, 1.0]
    payload = {
        "instruction": "move to center",
        "joint_state": [0.0] * 6,
        "image_b64": None,
    }
    r = httpx.post(f"{dummy_server_url}/predict", json=payload)
    chunk = r.json()["actions"]
    for step in chunk:
        for j, v in enumerate(step):
            assert MINS[j] <= v <= MAXS[j], f"joint {j} value {v} out of limits"


@pytest.mark.integration
def test_predict_accepts_null_image(dummy_server_url):
    payload = {
        "instruction": "release",
        "joint_state": [0.1, -0.2, 0.3, 0.0, 0.0, 0.5],
        "image_b64": None,
    }
    r = httpx.post(f"{dummy_server_url}/predict", json=payload)
    assert r.status_code == 200


@pytest.mark.integration
def test_predict_grasp_instruction_closes_gripper(dummy_server_url):
    """'grasp' 命令では gripper (joint 5) が閉じた値になる"""
    payload_grasp = {
        "instruction": "grasp gently",
        "joint_state": [0.0] * 6,
        "image_b64": None,
    }
    payload_release = {
        "instruction": "release and place down",
        "joint_state": [0.0] * 6,
        "image_b64": None,
    }
    grasp_chunk = httpx.post(f"{dummy_server_url}/predict", json=payload_grasp).json()["actions"]
    release_chunk = httpx.post(f"{dummy_server_url}/predict", json=payload_release).json()["actions"]

    # grasp: gripper > 0.3、release: gripper < 0.3
    assert grasp_chunk[-1][5] > 0.3, "grasp should close gripper"
    assert release_chunk[-1][5] < 0.3, "release should open gripper"


# ── Group B: SmolVLAClient 経由の本物 HTTP 通信 ───────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_smolvla_client_real_http(dummy_server_url):
    """SmolVLAClient が実際に HTTP POST し action chunk を返す (mock なし)"""
    from agents.smolvla_client import SmolVLAClient
    client = SmolVLAClient(endpoint_url=dummy_server_url)
    result = await client.predict(
        instruction="pick up the red cup",
        joint_state=[0.0] * 6,
        image_b64=None,
    )
    assert result is not None
    assert len(result) == 10
    assert all(len(step) == 6 for step in result)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_smolvla_client_returns_none_on_bad_url():
    """存在しないエンドポイントでは None が返る"""
    from agents.smolvla_client import SmolVLAClient
    client = SmolVLAClient(endpoint_url="http://127.0.0.1:1")  # closed port
    result = await client.predict("test", [0.0] * 6, None)
    assert result is None


# ── Group C: パイプライン統合 (ReasoningAgent だけモック) ──────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_smolvla_path_real_http(dummy_server_url, monkeypatch):
    """
    ReasoningAgent.reason() だけモックし、
    actions_to_instruction → SmolVLAClient(実HTTP) → DummyExecutor の全経路を確認
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from models.action import ActionPlan, ActionStep

    mock_plan = ActionPlan(
        reasoning="test",
        risk_level="low",
        risk_justification="safe",
        actions=[
            ActionStep(step=1, action="move_to", target="center", description="move"),
            ActionStep(step=2, action="grasp", force="gentle", description="grasp"),
        ],
        requires_approval=False,
    )

    executed_waypoints = []

    class CapturingExecutor:
        current = [0.0] * 6
        async def execute(self, waypoints, plan, broadcast_fn):
            executed_waypoints.extend(waypoints)

    import main as m
    monkeypatch.setattr("config.USE_SMOLVLA", True)
    monkeypatch.setenv("SMOLVLA_ENDPOINT_URL", dummy_server_url)

    # SmolVLAClient が dummy_server_url を使うよう endpoint_url を差し替え
    import agents.smolvla_client as sc_mod
    original_init = sc_mod.SmolVLAClient.__init__
    def patched_init(self, endpoint_url=None):
        original_init(self, endpoint_url=dummy_server_url)
    monkeypatch.setattr(sc_mod.SmolVLAClient, "__init__", patched_init)

    with patch("agents.reasoning.ReasoningAgent.reason", new_callable=AsyncMock, return_value=mock_plan), \
         patch("agents.executor.get_executor", return_value=CapturingExecutor()):
        broadcast_events = []
        async def mock_broadcast(event):
            broadcast_events.append(event)
        with patch.object(m, "broadcast", mock_broadcast):
            await m.run_pipeline("pick up the red cup")

    # EXEC_STEPS × MAX_CHUNKS ステップが executor に渡ったことを確認
    import config
    expected = config.SMOLVLA_EXEC_STEPS * config.SMOLVLA_MAX_CHUNKS
    assert len(executed_waypoints) == expected
    assert all(len(wp) == 6 for wp in executed_waypoints)
    # SmolVLA ステップが broadcast されたことを確認
    types = [e["type"] for e in broadcast_events]
    assert "reasoning_step" in types
