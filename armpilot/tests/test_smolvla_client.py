"""
Track 2: SmolVLAClient のテスト (DummyExecutor パターンで SmolVLA サーバー不要)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from agents.smolvla_client import SmolVLAClient, clamp_action_chunk
from config import JOINT_LIMITS


# --- clamp_action_chunk ---

def test_clamp_within_limits():
    chunk = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.5]]
    result = clamp_action_chunk(chunk)
    assert result == chunk


def test_clamp_clips_below_min():
    chunk = [[-99.0, 0.0, 0.0, 0.0, 0.0, -1.0]]
    result = clamp_action_chunk(chunk)
    assert result[0][0] == JOINT_LIMITS["min"][0]
    assert result[0][5] == JOINT_LIMITS["min"][5]


def test_clamp_clips_above_max():
    chunk = [[99.0, 0.0, 0.0, 0.0, 0.0, 99.0]]
    result = clamp_action_chunk(chunk)
    assert result[0][0] == JOINT_LIMITS["max"][0]
    assert result[0][5] == JOINT_LIMITS["max"][5]


def test_clamp_multiple_steps():
    chunk = [[-5.0, 0.0, 0.0, 0.0, 0.0, 0.5]] * 10
    result = clamp_action_chunk(chunk)
    assert len(result) == 10
    assert all(r[0] == JOINT_LIMITS["min"][0] for r in result)


# --- SmolVLAClient.predict (mock HTTP) ---

@pytest.mark.asyncio
async def test_predict_returns_action_chunk():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "actions": [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]] * 10
    }

    client = SmolVLAClient(endpoint_url="http://localhost:9999")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.predict(
            instruction="pick up the red cup",
            joint_state=[0.0] * 6,
            image_b64=None,
        )
    assert result is not None
    assert len(result) == 10
    assert len(result[0]) == 6


@pytest.mark.asyncio
async def test_predict_returns_none_on_timeout():
    import httpx
    client = SmolVLAClient(endpoint_url="http://localhost:9999")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
        result = await client.predict(
            instruction="pick up the red cup",
            joint_state=[0.0] * 6,
            image_b64=None,
        )
    assert result is None


@pytest.mark.asyncio
async def test_predict_returns_none_on_error():
    client = SmolVLAClient(endpoint_url="http://localhost:9999")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=Exception("connection refused")):
        result = await client.predict(
            instruction="pick up the red cup",
            joint_state=[0.0] * 6,
            image_b64=None,
        )
    assert result is None


@pytest.mark.asyncio
async def test_predict_clamps_chunk():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "actions": [[99.0, 0.0, 0.0, 0.0, 0.0, 99.0]] * 10
    }

    client = SmolVLAClient(endpoint_url="http://localhost:9999")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.predict("test", [0.0] * 6, None)
    assert result is not None
    assert result[0][0] == JOINT_LIMITS["max"][0]
    assert result[0][5] == JOINT_LIMITS["max"][5]
