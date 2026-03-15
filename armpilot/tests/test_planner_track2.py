"""
Track 2: actions_to_instruction() のテスト
"""
import pytest
from models.action import ActionPlan, ActionStep
from agents.planner import actions_to_instruction


def make_plan(actions: list[dict]) -> ActionPlan:
    return ActionPlan(
        reasoning="test",
        risk_level="low",
        risk_justification="test",
        actions=[ActionStep(**a) for a in actions],
        requires_approval=False,
    )


def test_basic_pick_and_place():
    plan = make_plan([
        {"step": 1, "action": "move_to", "target": "center", "description": "move above cup"},
        {"step": 2, "action": "grasp", "force": "gentle", "description": "pick up cup"},
        {"step": 3, "action": "move_to", "target": "far-left", "description": "carry to left"},
        {"step": 4, "action": "release", "description": "place down"},
    ])
    text = actions_to_instruction(plan)
    assert isinstance(text, str)
    assert len(text) > 0
    # キーワードが含まれること
    assert "center" in text or "pick" in text or "grasp" in text or "place" in text or "left" in text


def test_single_move():
    plan = make_plan([
        {"step": 1, "action": "move_to", "target": "home", "description": "return home"},
    ])
    text = actions_to_instruction(plan)
    assert "home" in text or "return" in text or "move" in text


def test_returns_nonempty_string():
    plan = make_plan([
        {"step": 1, "action": "pause", "description": "wait"},
    ])
    text = actions_to_instruction(plan)
    assert isinstance(text, str)
    assert len(text) > 0
