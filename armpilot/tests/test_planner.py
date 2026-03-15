"""
ActionPlanner.plan_to_waypoints() and actions_to_instruction() tests.
No robot hardware, no network calls.
"""
import pytest
from models.action import ActionPlan, ActionStep
from agents.planner import ActionPlanner, actions_to_instruction
from config import (
    POSITION_MAP,
    GRIPPER_OPEN,
    GRIPPER_CLOSED_GENTLE,
    GRIPPER_CLOSED_NORMAL,
    GRIPPER_CLOSED_FIRM,
)


def make_plan(actions: list[dict], risk: str = "low") -> ActionPlan:
    return ActionPlan(
        reasoning="test",
        risk_level=risk,
        risk_justification="test",
        actions=[ActionStep(**a) for a in actions],
        requires_approval=(risk != "low"),
    )


# ── plan_to_waypoints ──────────────────────────────────────────────────────


class TestPlanToWaypoints:
    def test_move_to_returns_position_from_map(self):
        plan = make_plan([{"step": 1, "action": "move_to", "target": "center", "description": "move"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert len(wps) == 1
        expected = list(POSITION_MAP["center"])
        expected[5] = 0.0  # gripper keeps current (0.0)
        assert wps[0] == expected

    def test_move_to_unknown_target_falls_back_to_center(self):
        plan = make_plan([{"step": 1, "action": "move_to", "target": "nonexistent", "description": "move"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        expected = list(POSITION_MAP["center"])
        expected[5] = 0.0
        assert wps[0] == expected

    def test_grasp_gentle_sets_gripper(self):
        plan = make_plan([{"step": 1, "action": "grasp", "force": "gentle", "description": "grasp"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == GRIPPER_CLOSED_GENTLE

    def test_grasp_normal_sets_gripper(self):
        plan = make_plan([{"step": 1, "action": "grasp", "force": "normal", "description": "grasp"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == GRIPPER_CLOSED_NORMAL

    def test_grasp_firm_sets_gripper(self):
        plan = make_plan([{"step": 1, "action": "grasp", "force": "firm", "description": "grasp"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == GRIPPER_CLOSED_FIRM

    def test_grasp_default_force_is_normal(self):
        """force=None defaults to GRIPPER_CLOSED_NORMAL"""
        plan = make_plan([{"step": 1, "action": "grasp", "description": "grasp"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == GRIPPER_CLOSED_NORMAL

    def test_release_opens_gripper(self):
        plan = make_plan([{"step": 1, "action": "release", "description": "release"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == GRIPPER_OPEN

    def test_pause_inserts_none(self):
        plan = make_plan([{"step": 1, "action": "pause", "description": "wait"}])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert len(wps) == 1
        assert wps[0] is None

    def test_full_pick_and_place_sequence(self):
        plan = make_plan([
            {"step": 1, "action": "move_to", "target": "center", "description": "approach"},
            {"step": 2, "action": "grasp", "force": "gentle", "description": "grasp"},
            {"step": 3, "action": "move_to", "target": "far-left", "description": "carry"},
            {"step": 4, "action": "release", "description": "place"},
        ])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        assert len(wps) == 4
        assert wps[0] is not None          # move_to → position
        assert wps[1][5] == GRIPPER_CLOSED_GENTLE  # grasp
        assert wps[2] is not None          # move_to
        assert wps[3][5] == GRIPPER_OPEN   # release

    def test_move_to_uses_planner_current_gripper(self):
        """move_to copies self.current[5] — initial current is 0.0"""
        plan = make_plan([
            {"step": 1, "action": "move_to", "target": "center", "description": "carry"},
        ])
        planner = ActionPlanner()
        planner.current[5] = 0.75  # simulate arm already holding something
        wps = planner.plan_to_waypoints(plan)
        assert wps[0][5] == 0.75

    def test_waypoints_are_6_dof(self):
        plan = make_plan([
            {"step": 1, "action": "move_to", "target": "center", "description": "move"},
            {"step": 2, "action": "grasp", "force": "normal", "description": "grasp"},
            {"step": 3, "action": "release", "description": "release"},
        ])
        planner = ActionPlanner()
        wps = planner.plan_to_waypoints(plan)
        for wp in wps:
            if wp is not None:
                assert len(wp) == 6


class TestValidate:
    def test_raises_on_out_of_limit_position(self, monkeypatch):
        """_validate raises ValueError if a joint exceeds JOINT_LIMITS"""
        import agents.planner as planner_mod
        monkeypatch.setitem(planner_mod.POSITION_MAP, "bad", [99.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        plan = make_plan([{"step": 1, "action": "move_to", "target": "bad", "description": "bad"}])
        planner = ActionPlanner()
        with pytest.raises(ValueError, match="Joint"):
            planner.plan_to_waypoints(plan)


# ── actions_to_instruction ─────────────────────────────────────────────────


class TestActionsToInstruction:
    def test_move_to_includes_target(self):
        plan = make_plan([{"step": 1, "action": "move_to", "target": "far-right", "description": "go right"}])
        text = actions_to_instruction(plan)
        assert "far-right" in text

    def test_grasp_includes_force(self):
        plan = make_plan([{"step": 1, "action": "grasp", "force": "gentle", "description": "grasp gently"}])
        text = actions_to_instruction(plan)
        assert "gentle" in text

    def test_release_present(self):
        plan = make_plan([{"step": 1, "action": "release", "description": "release"}])
        text = actions_to_instruction(plan)
        assert len(text) > 0
        assert "release" in text or "place" in text

    def test_pause_present(self):
        plan = make_plan([{"step": 1, "action": "pause", "description": "wait"}])
        text = actions_to_instruction(plan)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_multi_step_joined(self):
        plan = make_plan([
            {"step": 1, "action": "move_to", "target": "center", "description": "move"},
            {"step": 2, "action": "grasp", "force": "normal", "description": "grasp"},
        ])
        text = actions_to_instruction(plan)
        # Both steps should appear in one string (comma-joined)
        assert "center" in text
        assert "normal" in text

    def test_returns_string(self):
        plan = make_plan([{"step": 1, "action": "move_to", "target": "home", "description": "home"}])
        assert isinstance(actions_to_instruction(plan), str)

    def test_empty_actions_falls_back_to_reasoning(self):
        plan = ActionPlan(
            reasoning="fallback text",
            risk_level="low",
            risk_justification="safe",
            actions=[],
            requires_approval=False,
        )
        text = actions_to_instruction(plan)
        assert "fallback text" in text
