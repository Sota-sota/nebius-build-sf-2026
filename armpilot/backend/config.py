import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# ── LLM APIs ─────────────────────────────────────────────
NEBIUS_API_KEY          = os.getenv("NEBIUS_API_KEY")
NEBIUS_MODEL            = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
NEBIUS_VISION_MODEL     = os.getenv("NEBIUS_VISION_MODEL", "")  # empty = use OpenRouter

TAVILY_API_KEY          = os.getenv("TAVILY_API_KEY")

OPENROUTER_API_KEY      = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")

# ── Hardware ─────────────────────────────────────────────
ARM_PORT           = os.getenv("ARM_PORT", "/dev/ttyACM0")
ARM_ID             = os.getenv("ARM_ID", "armpilot_follower")
CAMERA_INDEX       = int(os.getenv("CAMERA_INDEX", "0"))

# ── Server ───────────────────────────────────────────────
BACKEND_HOST       = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT       = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT      = int(os.getenv("FRONTEND_PORT", "5173"))

# ── Camera ───────────────────────────────────────────────
FRAME_WIDTH        = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT       = int(os.getenv("FRAME_HEIGHT", "480"))
CAPTURE_INTERVAL   = float(os.getenv("CAPTURE_INTERVAL", "2.0"))

# ── Arm positions (calibrate with actual arm) ────────────
POSITION_MAP = {
    "home":         [0.0,   0.0,   0.0,   0.0,   0.0,   0.0],
    "far-left":     [-1.2, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-left":  [-0.6, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center":       [0.0,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-right": [0.6,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "far-right":    [1.2,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "above":        [0.0,  -0.2,   0.3,   0.0,   0.0,   0.0],
}

GRIPPER_OPEN          = 0.0
GRIPPER_CLOSED_GENTLE = 0.5
GRIPPER_CLOSED_NORMAL = 0.75
GRIPPER_CLOSED_FIRM   = 1.0

STEP_DELAY_S          = 0.3
INTERPOLATION_STEPS   = 5

JOINT_LIMITS = {
    "min": [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0],
    "max": [ 2.0,  2.0,  2.0,  2.0,  2.0, 1.0],
}
