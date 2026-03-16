"""
TDD tests for SmolVLA receding-horizon control loop (_run_smolvla_loop).

No real HTTP, no robot, no camera.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from models.action import ActionPlan, ActionStep

MOCK_PLAN = ActionPlan(
    reasoning="test",
    risk_level="low",
    risk_justification="safe",
    actions=[ActionStep(step=1, action="move_to", target="center", description="move")],
    requires_approval=False,
)

CHUNK_10 = [[float(i)] * 6 for i in range(10)]  # 10ステップのチャンク


def make_executor(start_joints=None):
    executor = MagicMock()
    executor.current = list(start_joints or [0.0] * 6)

    async def fake_execute(waypoints, plan, broadcast_fn):
        valid = [w for w in waypoints if w is not None]
        if valid:
            executor.current = list(valid[-1])

    executor.execute = AsyncMock(side_effect=fake_execute)
    return executor


def make_broadcast():
    events = []

    async def broadcast(event):
        events.append(event)

    broadcast.events = events
    return broadcast


# ── ループ回数 ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loop_calls_predict_max_chunks_times():
    """MAX_CHUNKSを超えない範囲でpredictが繰り返し呼ばれる。"""
    import main as m

    executor = make_executor()
    broadcast = make_broadcast()
    predict_mock = AsyncMock(return_value=CHUNK_10)

    with patch("config.SMOLVLA_MAX_CHUNKS", 5), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", predict_mock):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    assert predict_mock.call_count == 5


@pytest.mark.asyncio
async def test_loop_stops_early_when_predict_returns_none():
    """predictがNoneを返したらそこでループを終了する。"""
    import main as m

    executor = make_executor()
    broadcast = make_broadcast()
    predict_mock = AsyncMock(side_effect=[CHUNK_10, None, CHUNK_10])

    with patch("config.SMOLVLA_MAX_CHUNKS", 5), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", predict_mock):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    assert predict_mock.call_count == 2  # Noneの時点で停止


@pytest.mark.asyncio
async def test_loop_executes_only_exec_steps_per_chunk():
    """1チャンクのうちSMOLVLA_EXEC_STEPSステップだけexecuteに渡す。"""
    import main as m

    executor = make_executor()
    broadcast = make_broadcast()
    predict_mock = AsyncMock(return_value=CHUNK_10)

    with patch("config.SMOLVLA_MAX_CHUNKS", 1), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", predict_mock):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    executed_waypoints = executor.execute.call_args[0][0]
    assert len(executed_waypoints) == 4


@pytest.mark.asyncio
async def test_loop_passes_updated_joint_state_to_next_predict():
    """各predict呼び出しにexecutorの最新joint stateを渡す。"""
    import main as m

    executor = make_executor(start_joints=[0.0] * 6)
    broadcast = make_broadcast()
    call_joint_states = []

    async def fake_predict(self, instruction, joint_state, image_b64):
        call_joint_states.append(list(joint_state))
        return CHUNK_10

    with patch("config.SMOLVLA_MAX_CHUNKS", 3), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", fake_predict):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    # 1回目: 初期状態 [0.0]*6
    assert call_joint_states[0] == [0.0] * 6
    # 2回目以降: CHUNK_10の3インデックス目 = [3.0]*6
    assert call_joint_states[1] == [3.0] * 6
    assert call_joint_states[2] == [3.0] * 6


@pytest.mark.asyncio
async def test_loop_broadcasts_progress_each_chunk():
    """各チャンクの開始時にsmolvla_loopイベントをbroadcastする。"""
    import main as m

    executor = make_executor()
    broadcast = make_broadcast()
    predict_mock = AsyncMock(return_value=CHUNK_10)

    with patch("config.SMOLVLA_MAX_CHUNKS", 3), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", predict_mock):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    loop_events = [e for e in broadcast.events if e.get("data", {}).get("step") == "smolvla_loop"]
    assert len(loop_events) == 3


@pytest.mark.asyncio
async def test_loop_first_call_uses_executor_current():
    """初回predict呼び出しはexecutorの初期currentを使う。"""
    import main as m

    initial = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    executor = make_executor(start_joints=initial)
    broadcast = make_broadcast()
    first_joint = {}

    async def fake_predict(self, instruction, joint_state, image_b64):
        if "captured" not in first_joint:
            first_joint["captured"] = list(joint_state)
        return CHUNK_10

    with patch("config.SMOLVLA_MAX_CHUNKS", 1), \
         patch("config.SMOLVLA_EXEC_STEPS", 4), \
         patch("agents.smolvla_client.SmolVLAClient.predict", fake_predict):
        await m._run_smolvla_loop("pick up cup", executor, MOCK_PLAN, broadcast)

    assert first_joint["captured"] == initial
