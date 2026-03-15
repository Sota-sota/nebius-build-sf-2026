"""
VLM API wrapper — sends camera frames to a vision-language model
and returns structured scene descriptions.

Tries Nebius Token Factory first, falls back to OpenRouter.
"""

import asyncio
import json
import base64

from openai import OpenAI
from config import (
    NEBIUS_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_VISION_MODEL,
)

PERCEPTION_PROMPT = """You are a robotic perception system analyzing a workspace image for a 6-DOF robotic arm.

Analyze the image and return ONLY valid JSON (no markdown, no explanation):
{
    "objects": [
        {
            "id": "obj_1",
            "name": "red ceramic mug",
            "position": "center-left",
            "estimated_size": "medium",
            "color": "red",
            "material_guess": "ceramic",
            "graspable": true,
            "confidence": 0.85
        }
    ],
    "scene_description": "A desk workspace with...",
    "workspace_clear": true
}

Rules:
- position must be one of: "far-left", "center-left", "center", "center-right", "far-right"
- estimated_size must be one of: "tiny", "small", "medium", "large"
- Only include objects within arm reach
- Set graspable=false for objects too large/heavy/dangerous
"""

SIMPLE_PROMPT = """Analyze this workspace image for a robotic arm. Return ONLY valid JSON with this exact schema:
{"objects":[{"id":"obj_1","name":"...","position":"center","estimated_size":"small","color":"...","material_guess":"...","graspable":true,"confidence":0.8}],"scene_description":"...","workspace_clear":true}
position: far-left|center-left|center|center-right|far-right. estimated_size: tiny|small|medium|large."""


def _get_openrouter_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


def _get_nebius_client() -> OpenAI:
    return OpenAI(
        base_url="https://api.tokenfactory.nebius.com/v1",
        api_key=NEBIUS_API_KEY,
    )


def _build_vision_messages(frame_b64: str, prompt: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
                },
            ],
        }
    ]


def _parse_vlm_response(raw: str) -> dict:
    """Parse JSON from VLM response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def analyze_frame(frame_b64: str) -> dict:
    """
    Send a base64-encoded JPEG frame to a VLM and get structured scene data.
    Returns a dict matching the SceneDescription schema.
    Timeout: 10 seconds.
    """
    # Try OpenRouter (more reliable for vision)
    try:
        result = await asyncio.wait_for(
            _call_vlm(frame_b64, PERCEPTION_PROMPT),
            timeout=10.0,
        )
        return result
    except Exception as e:
        print(f"[Vision] First attempt failed: {e}")

    # Retry with simpler prompt
    try:
        result = await asyncio.wait_for(
            _call_vlm(frame_b64, SIMPLE_PROMPT),
            timeout=10.0,
        )
        return result
    except Exception as e:
        print(f"[Vision] Retry failed: {e}")
        return _fallback_scene()


async def _call_vlm(frame_b64: str, prompt: str) -> dict:
    """Call the VLM via OpenRouter."""
    client = _get_openrouter_client()
    messages = _build_vision_messages(frame_b64, prompt)

    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model=OPENROUTER_VISION_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1000,
        )
    )

    raw = response.choices[0].message.content
    return _parse_vlm_response(raw)


def _fallback_scene() -> dict:
    """Return a safe fallback scene when VLM fails."""
    return {
        "objects": [],
        "scene_description": "Unable to analyze scene — VLM unavailable",
        "workspace_clear": True,
    }
