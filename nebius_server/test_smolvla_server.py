"""
TDD tests for smolvla_server.py

Red phase: write tests first, then make them pass.

Run: pytest test_smolvla_server.py -v
"""

import base64
import io
import sys
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

# Add server dir to path
sys.path.insert(0, os.path.dirname(__file__))


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def make_dummy_image_b64(size: int = 64) -> str:
    """Create a small solid-color image and return as base64 JPEG."""
    img = Image.new("RGB", (size, size), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def make_mock_policy(n_steps: int = 10, action_dim: int = 6):
    """Return a mock SmolVLA policy whose predict_action_chunk returns a fixed tensor."""
    mock = MagicMock()
    # Shape: (1, n_steps, action_dim)
    mock.predict_action_chunk.return_value = torch.zeros(1, n_steps, action_dim)
    mock.config = MagicMock()
    return mock


def make_mock_preprocessor():
    """Preprocessor that returns its input unchanged (batch already on CPU)."""
    mock = MagicMock()
    mock.return_value = {}   # policy doesn't use the batch in mock mode
    return mock


def make_mock_postprocessor(n_steps: int = 10, action_dim: int = 6):
    """Postprocessor that returns a tensor of zeros."""
    mock = MagicMock()
    mock.return_value = torch.zeros(1, n_steps, action_dim)
    return mock


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def client_with_model():
    """TestClient with model already 'loaded' (mocked).

    We patch load_model() so the TestClient startup event doesn't try to
    import lerobot/transformers (not installed in test env).
    """
    import smolvla_server as srv

    mock_policy = make_mock_policy()
    mock_pre    = make_mock_preprocessor()
    mock_post   = make_mock_postprocessor()

    def fake_load():
        srv.policy       = mock_policy
        srv.preprocessor = mock_pre
        srv.postprocessor = mock_post

    with patch("smolvla_server.load_model", side_effect=fake_load):
        with TestClient(srv.app) as c:
            yield c

    srv.policy = srv.preprocessor = srv.postprocessor = None


@pytest.fixture
def client_no_model():
    """TestClient with model NOT loaded (simulates startup before model ready)."""
    import smolvla_server as srv

    def fake_load_noop():
        pass  # model stays None

    with patch("smolvla_server.load_model", side_effect=fake_load_noop):
        with TestClient(srv.app) as c:
            yield c


# -----------------------------------------------------------------------
# GET /health
# -----------------------------------------------------------------------

class TestHealth:
    def test_health_ok_when_model_loaded(self, client_with_model):
        r = client_with_model.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "model_id" in body
        assert "device" in body

    def test_health_loading_when_model_not_ready(self, client_no_model):
        r = client_no_model.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "loading"


# -----------------------------------------------------------------------
# POST /predict — happy path
# -----------------------------------------------------------------------

class TestPredictHappyPath:
    def test_returns_10_action_steps(self, client_with_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0, 0.1, -0.2, 0.3, 0.0, 0.5],
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["n_steps"] == 10
        assert len(body["actions"]) == 10
        assert len(body["actions"][0]) == 6

    def test_returns_inference_time_ms(self, client_with_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200
        assert r.json()["inference_time_ms"] > 0

    def test_returns_model_id(self, client_with_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200
        assert "model_id" in r.json()

    def test_accepts_image_b64(self, client_with_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
            "image_b64": make_dummy_image_b64(),
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200

    def test_accepts_no_image(self, client_with_model):
        """image_b64=None must still work (camera fallback)."""
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
            "image_b64": None,
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200


# -----------------------------------------------------------------------
# POST /predict — joint limit clamping (safety critical)
# -----------------------------------------------------------------------

class TestJointLimitClamping:
    def test_out_of_range_actions_are_clamped(self, client_with_model):
        """
        Policy outputs values outside JOINT_MIN/JOINT_MAX.
        Server must clamp them before returning.
        """
        import smolvla_server as srv

        # Postprocessor returns values way outside limits
        extreme = torch.full((1, 10, 6), 99.0)
        srv.postprocessor.return_value = extreme

        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 200

        actions = r.json()["actions"]
        for step in actions:
            for j, val in enumerate(step):
                assert val <= srv.JOINT_MAX[j], f"joint {j} value {val} exceeds max {srv.JOINT_MAX[j]}"
                assert val >= srv.JOINT_MIN[j], f"joint {j} value {val} below min {srv.JOINT_MIN[j]}"

    def test_negative_out_of_range_clamped(self, client_with_model):
        import smolvla_server as srv

        extreme = torch.full((1, 10, 6), -99.0)
        srv.postprocessor.return_value = extreme

        r = client_with_model.post("/predict", json={"instruction": "test", "joint_state": [0.0] * 6})
        assert r.status_code == 200

        actions = r.json()["actions"]
        for step in actions:
            for j, val in enumerate(step):
                assert val >= srv.JOINT_MIN[j]


# -----------------------------------------------------------------------
# POST /predict — validation errors
# -----------------------------------------------------------------------

class TestPredictValidation:
    def test_wrong_joint_state_length_returns_400(self, client_with_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0, 0.1, 0.2],  # only 3 values, need 6
        }
        r = client_with_model.post("/predict", json=payload)
        assert r.status_code == 400

    def test_model_not_loaded_returns_503(self, client_no_model):
        payload = {
            "instruction": "pick up the red cup",
            "joint_state": [0.0] * 6,
        }
        r = client_no_model.post("/predict", json=payload)
        assert r.status_code == 503


# -----------------------------------------------------------------------
# Helper: _decode_image
# -----------------------------------------------------------------------

class TestDecodeImage:
    def test_output_shape(self):
        from smolvla_server import _decode_image
        b64 = make_dummy_image_b64(size=128)
        tensor = _decode_image(b64)
        assert tensor.shape == (3, 256, 256)   # resized to IMAGE_SIZE

    def test_output_range(self):
        from smolvla_server import _decode_image
        b64 = make_dummy_image_b64()
        tensor = _decode_image(b64)
        assert tensor.min() >= 0.0
        assert tensor.max() <= 1.0


# -----------------------------------------------------------------------
# Helper: _clamp_to_joint_limits
# -----------------------------------------------------------------------

class TestClampToJointLimits:
    def test_clamp_above_max(self):
        from smolvla_server import _clamp_to_joint_limits, JOINT_MAX
        actions = np.full((10, 6), 99.0, dtype=np.float32)
        clamped = _clamp_to_joint_limits(actions)
        assert np.all(clamped <= np.array(JOINT_MAX))

    def test_clamp_below_min(self):
        from smolvla_server import _clamp_to_joint_limits, JOINT_MIN
        actions = np.full((10, 6), -99.0, dtype=np.float32)
        clamped = _clamp_to_joint_limits(actions)
        assert np.all(clamped >= np.array(JOINT_MIN))

    def test_in_range_unchanged(self):
        from smolvla_server import _clamp_to_joint_limits
        actions = np.zeros((10, 6), dtype=np.float32)
        clamped = _clamp_to_joint_limits(actions)
        np.testing.assert_array_equal(clamped, actions)
