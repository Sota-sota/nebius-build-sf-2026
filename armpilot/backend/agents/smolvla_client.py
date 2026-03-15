import base64
import io
import httpx
from config import JOINT_LIMITS, SMOLVLA_ENDPOINT_URL, SMOLVLA_TIMEOUT_S, CAMERA_INDEX


def clamp_action_chunk(chunk: list[list[float]]) -> list[list[float]]:
    """action chunk の各 joint 値を JOINT_LIMITS でクランプする"""
    mins = JOINT_LIMITS["min"]
    maxs = JOINT_LIMITS["max"]
    return [
        [max(mins[j], min(maxs[j], v)) for j, v in enumerate(step)]
        for step in chunk
    ]


def _capture_frame_b64() -> str | None:
    """OpenCV でカメラフレームを 256×256 JPEG → base64 文字列に変換する"""
    try:
        import cv2
        cap = cv2.VideoCapture(CAMERA_INDEX)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return None
        frame = cv2.resize(frame, (256, 256))
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception:
        return None


class SmolVLAClient:
    def __init__(self, endpoint_url: str | None = None):
        self.endpoint_url = (endpoint_url or SMOLVLA_ENDPOINT_URL).rstrip("/")

    async def predict(
        self,
        instruction: str,
        joint_state: list[float],
        image_b64: str | None,
    ) -> list[list[float]] | None:
        """
        SmolVLA サーバーに POST /predict を送り、action chunk [10×6] を返す。
        失敗・タイムアウト時は None を返す（フォールバック用）。
        image_b64=None の場合はカメラから自動キャプチャを試みる。
        """
        if not self.endpoint_url:
            return None

        # カメラフレーム取得（引数で渡されない場合）
        frame = image_b64 if image_b64 is not None else _capture_frame_b64()

        payload = {
            "instruction": instruction,
            "joint_state": joint_state,
            "image_b64": frame,
        }

        try:
            async with httpx.AsyncClient(timeout=SMOLVLA_TIMEOUT_S) as client:
                response = await client.post(
                    f"{self.endpoint_url}/predict",
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            chunk = data["action_chunk"]
            return clamp_action_chunk(chunk)
        except Exception:
            return None
