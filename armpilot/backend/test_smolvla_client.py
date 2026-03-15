"""
TDD tests for agents/smolvla_client.py

Run: cd armpilot/backend && pytest test_smolvla_client.py -v
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock


# -----------------------------------------------------------------------
# clamp_action_chunk
# -----------------------------------------------------------------------

class TestClampActionChunk:
    def test_clamps_above_max(self):
        from agents.smolvla_client import clamp_action_chunk
        chunk = [[99.0] * 6] * 10
        result = clamp_action_chunk(chunk)
        # joint 5 (gripper) max is 1.0, joints 0-4 max is 2.0
        for step in result:
            for j in range(5):
                assert step[j] == 2.0
            assert step[5] == 1.0

    def test_clamps_below_min(self):
        from agents.smolvla_client import clamp_action_chunk
        chunk = [[-99.0] * 6] * 10
        result = clamp_action_chunk(chunk)
        for step in result:
            for j in range(5):
                assert step[j] == -2.0
            assert step[5] == 0.0

    def test_in_range_unchanged(self):
        from agents.smolvla_client import clamp_action_chunk
        chunk = [[0.0, 0.5, -0.5, 1.0, -1.0, 0.5]] * 5
        result = clamp_action_chunk(chunk)
        assert result == chunk


# -----------------------------------------------------------------------
# SmolVLAClient.predict — happy path
# -----------------------------------------------------------------------

class TestSmolVLAClientPredict:
    @pytest.mark.asyncio
    async def test_returns_action_chunk_on_success(self):
        from agents.smolvla_client import SmolVLAClient

        fake_actions = [[0.1 * i] * 6 for i in range(10)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"actions": fake_actions, "n_steps": 10}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            client = SmolVLAClient(endpoint_url="http://fake:8001")
            result = await client.predict("pick up cup", [0.0] * 6, None)

        assert result is not None
        assert len(result) == 10
        assert len(result[0]) == 6

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        from agents.smolvla_client import SmolVLAClient

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            client = SmolVLAClient(endpoint_url="http://fake:8001")
            result = await client.predict("pick up cup", [0.0] * 6, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_endpoint(self):
        from agents.smolvla_client import SmolVLAClient
        client = SmolVLAClient(endpoint_url="")
        result = await client.predict("pick up cup", [0.0] * 6, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_actions_are_clamped(self):
        from agents.smolvla_client import SmolVLAClient

        # Server returns out-of-range values
        extreme_actions = [[99.0] * 6] * 10
        mock_response = MagicMock()
        mock_response.json.return_value = {"actions": extreme_actions, "n_steps": 10}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            client = SmolVLAClient(endpoint_url="http://fake:8001")
            result = await client.predict("pick up cup", [0.0] * 6, None)

        assert result is not None
        for step in result:
            assert step[5] <= 1.0  # gripper max
            for j in range(5):
                assert step[j] <= 2.0


# -----------------------------------------------------------------------
# actions_to_instruction
# -----------------------------------------------------------------------

class TestActionsToInstruction:
    def test_basic_pick_and_place(self):
        from agents.planner import actions_to_instruction
        from models.action import ActionPlan, ActionStep

        plan = ActionPlan(
            reasoning="pick up the cup",
            risk_level="low",
            risk_justification="simple task",
            actions=[
                ActionStep(step=1, action="move_to", target="center", description="move to center"),
                ActionStep(step=2, action="grasp", force="normal", description="grasp"),
                ActionStep(step=3, action="move_to", target="far-right", description="move to far-right"),
                ActionStep(step=4, action="release", description="release"),
            ],
            requires_approval=False,
        )
        instruction = actions_to_instruction(plan)
        assert "move to center" in instruction
        assert "grasp" in instruction
        assert "move to far-right" in instruction
        assert "release" in instruction

    def test_empty_actions_returns_reasoning(self):
        from agents.planner import actions_to_instruction
        from models.action import ActionPlan

        plan = ActionPlan(
            reasoning="do something",
            risk_level="low",
            risk_justification="simple",
            actions=[],
            requires_approval=False,
        )
        assert actions_to_instruction(plan) == "do something"
