"""
DummyExecutor and helper function tests.
No robot hardware (ArmExecutor never instantiated).
"""
import pytest
from models.action import ActionPlan, ActionStep
from agents.executor import DummyExecutor, interpolate, pos_list_to_action


def make_plan(risk: str = "low") -> ActionPlan:
    return ActionPlan(
        reasoning="test",
        risk_level=risk,
        risk_justification="test",
        actions=[ActionStep(step=1, action="move_to", target="center", description="move")],
        requires_approval=False,
    )


# ── interpolate ────────────────────────────────────────────────────────────


class TestInterpolate:
    def test_returns_correct_step_count(self):
        result = interpolate([0.0] * 6, [1.0] * 6, steps=5)
        assert len(result) == 5

    def test_final_step_equals_end(self):
        start = [0.0] * 6
        end = [1.0] * 6
        result = interpolate(start, end, steps=5)
        assert result[-1] == pytest.approx(end, abs=1e-9)

    def test_first_step_is_not_start(self):
        start = [0.0] * 6
        end = [1.0] * 6
        result = interpolate(start, end, steps=5)
        assert result[0] != start  # first intermediate, not start itself

    def test_intermediate_values_between_start_and_end(self):
        start = [0.0] * 6
        end = [2.0] * 6
        result = interpolate(start, end, steps=4)
        for step in result:
            for v in step:
                assert 0.0 < v <= 2.0

    def test_single_step_equals_end(self):
        start = [0.0] * 6
        end = [1.5, -0.5, 0.3, 0.0, 0.1, 0.8]
        result = interpolate(start, end, steps=1)
        assert len(result) == 1
        assert result[0] == pytest.approx(end, abs=1e-9)


# ── pos_list_to_action ─────────────────────────────────────────────────────


class TestPosListToAction:
    def test_keys_match_motor_names(self):
        pos = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        action = pos_list_to_action(pos)
        expected_keys = {
            "shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
            "wrist_flex.pos", "wrist_roll.pos", "gripper.pos",
        }
        assert set(action.keys()) == expected_keys

    def test_values_match_input(self):
        pos = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        action = pos_list_to_action(pos)
        assert action["shoulder_pan.pos"] == pytest.approx(0.1)
        assert action["gripper.pos"] == pytest.approx(0.6)

    def test_zero_position(self):
        pos = [0.0] * 6
        action = pos_list_to_action(pos)
        assert all(v == 0.0 for v in action.values())


# ── DummyExecutor ──────────────────────────────────────────────────────────


class TestDummyExecutor:
    @pytest.mark.asyncio
    async def test_broadcasts_executing_event(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        waypoints = [[0.0, -0.4, 0.5, 0.0, 0.0, 0.0]]
        await executor.execute(waypoints, plan, collect)

        types = [e["type"] for e in events]
        assert "reasoning_step" in types
        assert "execution_update" in types

    @pytest.mark.asyncio
    async def test_broadcasts_completed_at_end(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        waypoints = [[0.1, -0.4, 0.5, 0.0, 0.0, 0.0]]
        await executor.execute(waypoints, plan, collect)

        final = events[-1]
        assert final["data"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_skips_none_waypoints(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        # None = pause step; should not emit execution_update for it
        waypoints = [None, [0.0, -0.4, 0.5, 0.0, 0.0, 0.0]]
        await executor.execute(waypoints, plan, collect)

        update_events = [e for e in events if e["type"] == "execution_update"]
        # Only 1 real waypoint → at most 2 update events (step + completed)
        step_events = [e for e in update_events if e["data"].get("status") == "executing"]
        assert len(step_events) == 1

    @pytest.mark.asyncio
    async def test_execution_update_has_joint_positions(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        wp = [0.1, -0.3, 0.4, 0.0, 0.05, 0.5]
        await executor.execute([wp], plan, collect)

        step_events = [
            e for e in events
            if e["type"] == "execution_update" and e["data"].get("status") == "executing"
        ]
        assert len(step_events) == 1
        assert "joint_positions" in step_events[0]["data"]
        assert len(step_events[0]["data"]["joint_positions"]) == 5

    @pytest.mark.asyncio
    async def test_gripper_state_open_when_below_threshold(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        wp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.05]  # gripper < 0.1 → open
        await executor.execute([wp], plan, collect)

        step_events = [
            e for e in events
            if e["type"] == "execution_update" and e["data"].get("status") == "executing"
        ]
        assert step_events[0]["data"]["gripper_state"] == "open"

    @pytest.mark.asyncio
    async def test_gripper_state_closed_when_above_threshold(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        wp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.8]  # gripper > 0.1 → closed
        await executor.execute([wp], plan, collect)

        step_events = [
            e for e in events
            if e["type"] == "execution_update" and e["data"].get("status") == "executing"
        ]
        assert step_events[0]["data"]["gripper_state"] == "closed"

    @pytest.mark.asyncio
    async def test_empty_waypoints_still_broadcasts_completed(self):
        events = []

        async def collect(event):
            events.append(event)

        plan = make_plan()
        executor = DummyExecutor()
        await executor.execute([], plan, collect)

        types = [e["type"] for e in events]
        assert "execution_update" in types
        final = [e for e in events if e["type"] == "execution_update"][-1]
        assert final["data"]["status"] == "completed"
