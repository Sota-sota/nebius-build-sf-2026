"""
SmolVLA Inference Server — runs on Nebius GPU VM

Model: lerobot-edinburgh-white-team/smolvla_svla_so101_pickplace
  - Fine-tuned on SO101 pick-and-place
  - Input : observation.state (6), camera image (256x256), instruction text
  - Output: action chunk [10 x 6 joint angles]

Deploy:
  pip install -r requirements.txt
  uvicorn smolvla_server:app --host 0.0.0.0 --port 8001

Test:
  curl http://localhost:8001/health
"""

import base64
import io
import time
import logging
import os

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smolvla_server")

# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------
MODEL_ID = os.getenv(
    "SMOLVLA_MODEL_ID",
    "lerobot-edinburgh-white-team/smolvla_svla_so101_pickplace",
)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IMAGE_SIZE = 256  # resize input images to this square

# SO101 joint limits — clamp all output actions to these ranges to prevent runaway
JOINT_MIN = [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0]
JOINT_MAX = [2.0, 2.0, 2.0, 2.0, 2.0, 1.0]

# -----------------------------------------------------------------------
# Global model state (loaded once at startup)
# -----------------------------------------------------------------------
policy = None
preprocessor = None
postprocessor = None


# -----------------------------------------------------------------------
# Request / Response schemas
# -----------------------------------------------------------------------
class PredictRequest(BaseModel):
    instruction: str
    joint_state: list[float]         # 6 values, current joint angles
    image_b64: str | None = None     # base64 JPEG/PNG, any resolution — will be resized


class PredictResponse(BaseModel):
    actions: list[list[float]]       # [n_action_steps x 6]
    n_steps: int
    model_id: str
    inference_time_ms: float


# -----------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    import smolvla_server as _self
    _self.load_model()
    yield


app = FastAPI(title="SmolVLA Inference Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_model():
    """Load SmolVLA policy + processors into global state.

    Defined as a module-level function (not inline in the decorator) so that
    tests can patch `smolvla_server.load_model` and the startup handler picks
    up the patched version via dynamic attribute lookup.
    """
    global policy, preprocessor, postprocessor

    logger.info(f"Loading model: {MODEL_ID}  device={DEVICE}")
    t0 = time.perf_counter()

    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from lerobot.policies.factory import make_pre_post_processors

    policy = SmolVLAPolicy.from_pretrained(MODEL_ID)
    policy.to(DEVICE)
    policy.eval()

    from lerobot.policies.smolvla.processor_smolvla import make_smolvla_pre_post_processors
    policy.config.device = DEVICE
    preprocessor, postprocessor = make_smolvla_pre_post_processors(
        policy.config,
        dataset_stats=None,  # normalization handled inside policy weights
    )

    elapsed = time.perf_counter() - t0
    logger.info(f"Model ready in {elapsed:.1f}s  (device={DEVICE})")




# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok" if policy is not None else "loading",
        "model_id": MODEL_ID,
        "device": DEVICE,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if policy is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    if len(req.joint_state) != 6:
        raise HTTPException(status_code=400, detail=f"joint_state must have 6 values, got {len(req.joint_state)}")

    t0 = time.perf_counter()

    # --- Build observation dict ---
    observation = {
        "observation.state": torch.tensor(req.joint_state, dtype=torch.float32),
    }

    # Camera image — model requires at least one image key
    # Model was trained with observation.images.up and observation.images.side
    if req.image_b64 is not None:
        image = _decode_image(req.image_b64)  # (3, H, W) float32 [0,1]
    else:
        # Dummy black image fallback when no camera available
        image = torch.zeros(3, IMAGE_SIZE, IMAGE_SIZE, dtype=torch.float32)
    observation["observation.images.up"] = image
    observation["observation.images.side"] = image

    complementary = {"task": req.instruction}

    # --- Preprocessor pipeline (tokenise, normalise, add batch dim, move to device) ---
    batch = preprocessor({**observation, **{"task": req.instruction}})

    # --- Inference ---
    with torch.inference_mode():
        # predict_action_chunk returns (B, n_action_steps, action_dim)
        action_chunk = policy.predict_action_chunk(batch)

    # --- Postprocessor (unnormalise, move to CPU) ---
    action_chunk_cpu = postprocessor(action_chunk)  # still (B, n_steps, 6)

    # Extract first batch element → (n_steps, 6)
    if isinstance(action_chunk_cpu, torch.Tensor):
        actions_np = action_chunk_cpu[0].numpy()
    else:
        actions_np = np.array(action_chunk_cpu)

    # --- Safety clamp ---
    actions_np = _clamp_to_joint_limits(actions_np)

    inference_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"/predict  instruction='{req.instruction[:60]}'  {inference_ms:.0f}ms  shape={actions_np.shape}")

    return PredictResponse(
        actions=actions_np.tolist(),
        n_steps=int(actions_np.shape[0]),
        model_id=MODEL_ID,
        inference_time_ms=inference_ms,
    )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def _decode_image(b64_str: str) -> torch.Tensor:
    """base64 → (3, IMAGE_SIZE, IMAGE_SIZE) float32 tensor in [0, 1]."""
    raw = base64.b64decode(b64_str)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0   # (H, W, 3)
    return torch.from_numpy(arr).permute(2, 0, 1)   # (3, H, W)


def _clamp_to_joint_limits(actions: np.ndarray) -> np.ndarray:
    """Clamp (n_steps, 6) array to JOINT_MIN/JOINT_MAX per joint."""
    lo = np.array(JOINT_MIN, dtype=np.float32)
    hi = np.array(JOINT_MAX, dtype=np.float32)
    return np.clip(actions, lo, hi)
