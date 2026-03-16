import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

NEBIUS_API_KEY     = os.getenv("NEBIUS_API_KEY")
NEBIUS_MODEL       = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
TAVILY_API_KEY     = os.getenv("TAVILY_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
ARM_PORT           = os.getenv("ARM_PORT", "/dev/ttyACM0")
ARM_ID             = os.getenv("ARM_ID", "armpilot_follower")
CAMERA_INDEX       = int(os.getenv("CAMERA_INDEX", "0"))
BACKEND_PORT       = int(os.getenv("BACKEND_PORT", "8000"))

# ← アーム校正後に実測値で更新する
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

JOINT_LIMITS = {
    "min": [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0],
    "max": [ 2.0,  2.0,  2.0,  2.0,  2.0, 1.0],
}

# SmolVLA (Track 2)
SMOLVLA_ENDPOINT_URL = os.getenv("SMOLVLA_ENDPOINT_URL", "")
SMOLVLA_TIMEOUT_S    = float(os.getenv("SMOLVLA_TIMEOUT_S", "10"))
USE_SMOLVLA          = os.getenv("USE_SMOLVLA", "false").lower() == "true"
SMOLVLA_MAX_CHUNKS   = int(os.getenv("SMOLVLA_MAX_CHUNKS", "20"))   # タスク完了までの最大推論回数
SMOLVLA_EXEC_STEPS   = int(os.getenv("SMOLVLA_EXEC_STEPS", "4"))    # 1チャンクのうち実際に実行するステップ数
