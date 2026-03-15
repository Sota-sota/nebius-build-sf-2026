"""
Dummy SmolVLA サーバー — Track 1 VM なしで HTTP パスを部分テストするためのスタブ。
Track 1 の smolvla_server.py と完全に同じ API スキーマ。

起動方法:
  cd armpilot/backend
  PYTHONPATH=. python ../scripts/dummy_smolvla_server.py

.env に設定:
  SMOLVLA_ENDPOINT_URL=http://localhost:9999
  USE_SMOLVLA=true
"""
import math
import sys
import os

from fastapi import FastAPI
from pydantic import BaseModel

# JOINT_LIMITS (config.py と同値 — 依存を避けるためリテラル)
_JOINT_MIN = [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0]
_JOINT_MAX = [ 2.0,  2.0,  2.0,  2.0,  2.0, 1.0]

app = FastAPI(title="DummySmolVLA", version="0.1.0")


class PredictRequest(BaseModel):
    instruction: str
    joint_state: list[float]
    image_b64: str | None = None


class PredictResponse(BaseModel):
    actions: list[list[float]]
    model: str = "dummy"


def _make_chunk(instruction: str, joint_state: list[float]) -> list[list[float]]:
    """
    instruction と joint_state から決定論的に action chunk [10×6] を生成する。
    - 'grasp' を含む命令: gripper (joint 5) を段階的に閉じる (→ 0.7)
    - 'release' を含む命令: gripper を段階的に開く (→ 0.0)
    - それ以外: joint_state を維持しつつわずかに変化
    全値は JOINT_LIMITS 内に収まる。
    """
    is_grasp   = "grasp" in instruction.lower()
    is_release = "release" in instruction.lower() or "place" in instruction.lower()

    chunk = []
    for i in range(10):
        t = (i + 1) / 10  # 0.1 → 1.0
        step = []
        for j in range(6):
            if j == 5:
                # gripper
                if is_grasp:
                    val = 0.7 * t
                elif is_release:
                    start = joint_state[5] if len(joint_state) > 5 else 0.0
                    val = start * (1 - t)
                else:
                    val = joint_state[5] if len(joint_state) > 5 else 0.0
            else:
                # arm joints: 現在位置から微小変動 (sin波)
                base = joint_state[j] if len(joint_state) > j else 0.0
                val = base + 0.05 * math.sin(t * math.pi + j)
            # clamp
            val = max(_JOINT_MIN[j], min(_JOINT_MAX[j], val))
            step.append(round(val, 4))
        chunk.append(step)
    return chunk


@app.get("/health")
def health():
    return {"status": "ok", "model": "dummy"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    chunk = _make_chunk(req.instruction, req.joint_state)
    return PredictResponse(actions=chunk)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DUMMY_SMOLVLA_PORT", "9999"))
    print(f"[DummySmolVLA] Starting on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
