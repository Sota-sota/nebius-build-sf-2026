"""
Perception agent — captures frames from USB camera,
sends to VLM for scene analysis, and broadcasts results.
"""

import asyncio
import base64
import time
from typing import Callable, Optional

from config import CAMERA_INDEX
from models.scene import SceneDescription, DetectedObject
from tools.vision import analyze_frame

# Camera settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CAPTURE_INTERVAL = 2.0  # seconds between auto-captures for streaming
VLM_COOLDOWN = 5.0  # minimum seconds between VLM calls


class PerceptionAgent:
    def __init__(self):
        self._cap = None
        self._last_vlm_call = 0.0
        self._latest_scene: Optional[SceneDescription] = None
        self._streaming = False

    def _get_camera(self):
        """Lazy-init camera capture."""
        if self._cap is None:
            try:
                import cv2
                cap = cv2.VideoCapture(CAMERA_INDEX)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                if cap.isOpened():
                    self._cap = cap
                    print(f"[Perception] Camera {CAMERA_INDEX} opened ({FRAME_WIDTH}x{FRAME_HEIGHT})")
                else:
                    print(f"[Perception] Camera {CAMERA_INDEX} failed to open")
            except ImportError:
                print("[Perception] opencv-python not installed — camera unavailable")
        return self._cap

    def _capture_frame_b64(self) -> Optional[str]:
        """Capture a single frame, return as base64 JPEG string."""
        cap = self._get_camera()
        if cap is None:
            return None

        import cv2
        ret, frame = cap.read()
        if not ret:
            return None

        # Encode as JPEG (quality=50 for speed)
        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return base64.b64encode(jpeg.tobytes()).decode("utf-8")

    async def capture_and_analyze(self, broadcast_fn: Callable) -> Optional[SceneDescription]:
        """
        Capture a frame, send to VLM, parse into SceneDescription.
        Broadcasts perception_result to frontend.
        """
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "perceiving", "detail": "Capturing and analyzing scene..."},
        })

        start = time.time()
        frame_b64 = await asyncio.to_thread(self._capture_frame_b64)

        if frame_b64 is None:
            # No camera — return None, caller should use mock scene
            return None

        # Broadcast raw frame
        await broadcast_fn({
            "type": "camera_frame",
            "data": {
                "frame_b64": frame_b64,
                "width": FRAME_WIDTH,
                "height": FRAME_HEIGHT,
            },
        })

        # Call VLM
        scene_data = await analyze_frame(frame_b64)
        latency_ms = int((time.time() - start) * 1000)

        # Parse into Pydantic model
        try:
            scene = SceneDescription(
                objects=[DetectedObject(**o) for o in scene_data.get("objects", [])],
                scene_description=scene_data.get("scene_description", ""),
                workspace_clear=scene_data.get("workspace_clear", True),
            )
        except Exception as e:
            print(f"[Perception] Failed to parse VLM response: {e}")
            scene = SceneDescription(
                objects=[],
                scene_description="Parse error — falling back to empty scene",
                workspace_clear=True,
            )

        self._latest_scene = scene
        self._last_vlm_call = time.time()

        await broadcast_fn({
            "type": "perception_result",
            "data": scene.model_dump(mode="json"),
            "latency_ms": latency_ms,
        })

        return scene

    async def stream_camera(self, broadcast_fn: Callable):
        """
        Continuously stream camera frames at ~2 FPS.
        Does NOT call VLM — just broadcasts raw frames.
        """
        self._streaming = True
        print("[Perception] Starting camera stream...")
        while self._streaming:
            frame_b64 = await asyncio.to_thread(self._capture_frame_b64)
            if frame_b64:
                await broadcast_fn({
                    "type": "camera_frame",
                    "data": {
                        "frame_b64": frame_b64,
                        "width": FRAME_WIDTH,
                        "height": FRAME_HEIGHT,
                    },
                })
            await asyncio.sleep(CAPTURE_INTERVAL)

    def stop_stream(self):
        self._streaming = False

    @property
    def latest_scene(self) -> Optional[SceneDescription]:
        return self._latest_scene

    @property
    def has_camera(self) -> bool:
        cap = self._get_camera()
        return cap is not None and cap.isOpened()

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
