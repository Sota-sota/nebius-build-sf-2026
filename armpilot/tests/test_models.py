"""
Pydantic model validation tests for ActionStep and ActionPlan.
"""
import pytest
from pydantic import ValidationError
from models.action import ActionStep, ActionPlan


class TestActionStep:
    def test_valid_move_to(self):
        step = ActionStep(step=1, action="move_to", target="center", description="move")
        assert step.action == "move_to"
        assert step.target == "center"

    def test_valid_grasp(self):
        step = ActionStep(step=2, action="grasp", force="gentle", description="grasp")
        assert step.force == "gentle"

    def test_valid_release(self):
        step = ActionStep(step=3, action="release", description="release")
        assert step.action == "release"

    def test_valid_pause(self):
        step = ActionStep(step=4, action="pause", description="wait")
        assert step.action == "pause"

    def test_invalid_action_raises(self):
        with pytest.raises(ValidationError):
            ActionStep(step=1, action="fly", description="invalid action")

    def test_invalid_force_raises(self):
        with pytest.raises(ValidationError):
            ActionStep(step=1, action="grasp", force="super-hard", description="bad force")

    def test_target_defaults_none(self):
        step = ActionStep(step=1, action="release", description="release")
        assert step.target is None

    def test_force_defaults_none(self):
        step = ActionStep(step=1, action="move_to", target="center", description="move")
        assert step.force is None


class TestActionPlan:
    def _base_plan_kwargs(self):
        return dict(
            reasoning="test reasoning",
            risk_level="low",
            risk_justification="safe",
            actions=[
                ActionStep(step=1, action="move_to", target="center", description="move")
            ],
            requires_approval=False,
        )

    def test_valid_plan(self):
        plan = ActionPlan(**self._base_plan_kwargs())
        assert plan.risk_level == "low"
        assert len(plan.actions) == 1

    def test_action_id_auto_generated(self):
        plan = ActionPlan(**self._base_plan_kwargs())
        assert isinstance(plan.action_id, str)
        assert len(plan.action_id) > 0

    def test_two_plans_have_different_ids(self):
        plan1 = ActionPlan(**self._base_plan_kwargs())
        plan2 = ActionPlan(**self._base_plan_kwargs())
        assert plan1.action_id != plan2.action_id

    def test_invalid_risk_level_raises(self):
        kwargs = self._base_plan_kwargs()
        kwargs["risk_level"] = "extreme"
        with pytest.raises(ValidationError):
            ActionPlan(**kwargs)

    def test_risk_level_medium(self):
        kwargs = self._base_plan_kwargs()
        kwargs["risk_level"] = "medium"
        kwargs["requires_approval"] = True
        plan = ActionPlan(**kwargs)
        assert plan.risk_level == "medium"

    def test_risk_level_high(self):
        kwargs = self._base_plan_kwargs()
        kwargs["risk_level"] = "high"
        kwargs["requires_approval"] = True
        plan = ActionPlan(**kwargs)
        assert plan.risk_level == "high"

    def test_tavily_queries_defaults_empty(self):
        plan = ActionPlan(**self._base_plan_kwargs())
        assert plan.tavily_queries_used == []

    def test_knowledge_summary_defaults_empty(self):
        plan = ActionPlan(**self._base_plan_kwargs())
        assert plan.knowledge_summary == ""

    def test_empty_actions_allowed(self):
        kwargs = self._base_plan_kwargs()
        kwargs["actions"] = []
        plan = ActionPlan(**kwargs)
        assert plan.actions == []

    def test_multiple_actions(self):
        kwargs = self._base_plan_kwargs()
        kwargs["actions"] = [
            ActionStep(step=1, action="move_to", target="center", description="move"),
            ActionStep(step=2, action="grasp", force="gentle", description="grasp"),
            ActionStep(step=3, action="release", description="release"),
        ]
        plan = ActionPlan(**kwargs)
        assert len(plan.actions) == 3
