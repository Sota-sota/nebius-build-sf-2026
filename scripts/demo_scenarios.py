"""
Pre-scripted demo scenarios for ArmPilot hackathon judging.
Sends mock WebSocket events to the frontend for testing without the real backend.

Usage:
    python scripts/demo_scenarios.py [scenario]

    Scenarios: smart_pick, sort, safety, all
"""

import asyncio
import json
import sys
import time
import websockets

WS_URL = "ws://localhost:8000/ws"


def ts():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


SCENARIOS = {
    "smart_pick": [
        {"type": "perception_result", "data": {
            "objects": [
                {"id": "obj_1", "name": "red ceramic mug", "position": "center-left",
                 "estimated_size": "medium", "color": "red", "material_guess": "ceramic",
                 "graspable": True, "confidence": 0.92}
            ],
            "scene_description": "A desk workspace with a red ceramic mug at center-left",
            "workspace_clear": True
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "perceiving",
            "detail": "Detected 1 object: red ceramic mug at center-left (92% confidence)"
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "searching",
            "detail": "Searching for ceramic mug handling properties...",
            "tavily_query": "ceramic mug safe robotic grip force"
        }, "timestamp": ts()},
        {"type": "tavily_result", "data": {
            "query": "ceramic mug safe robotic grip force",
            "results": [
                {"title": "Robotic Grasping of Ceramic Objects",
                 "content": "Ceramic mugs typically weigh 300-400g. A gentle grip force of 2-5N is recommended to avoid fracture. The handle provides the most stable grip point.",
                 "url": "https://example.com/robotic-grasping"},
                {"title": "Material Properties of Ceramics",
                 "content": "Glazed ceramics have a coefficient of friction of 0.3-0.5. They are brittle and can chip under point loads exceeding 50N.",
                 "url": "https://example.com/ceramics"}
            ]
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "planning",
            "detail": "Planning 4-step gentle pick sequence based on ceramic fragility data"
        }, "timestamp": ts()},
        {"type": "action_plan", "data": {
            "action_id": "demo_001",
            "reasoning": "The ceramic mug weighs ~350g and is fragile. Using gentle grip force based on web search findings about ceramic handling.",
            "risk_level": "low",
            "risk_justification": "Common household object, well-understood material properties",
            "actions": [
                {"step": 1, "action": "move_to", "target": "center-left", "description": "Approach mug"},
                {"step": 2, "action": "grasp", "force": "gentle", "description": "Grip ceramic mug gently"},
                {"step": 3, "action": "move_to", "target": "above", "description": "Lift mug"},
                {"step": 4, "action": "move_to", "target": "center", "description": "Hold for display"}
            ],
            "requires_approval": False
        }, "timestamp": ts()},
        {"type": "execution_update", "data": {
            "current_step": 1, "total_steps": 4,
            "joint_positions": [-0.6, -0.4, 0.5, 0.0, 0.0, 0.0],
            "gripper_state": "open", "status": "executing"
        }, "timestamp": ts()},
        {"type": "execution_update", "data": {
            "current_step": 2, "total_steps": 4,
            "joint_positions": [-0.6, -0.4, 0.5, 0.0, 0.0, 0.5],
            "gripper_state": "closing", "status": "executing"
        }, "timestamp": ts()},
        {"type": "execution_update", "data": {
            "current_step": 3, "total_steps": 4,
            "joint_positions": [-0.6, -0.2, 0.3, 0.0, 0.0, 0.5],
            "gripper_state": "closed", "status": "executing"
        }, "timestamp": ts()},
        {"type": "execution_update", "data": {
            "current_step": 4, "total_steps": 4,
            "joint_positions": [0.0, -0.2, 0.3, 0.0, 0.0, 0.5],
            "gripper_state": "closed", "status": "completed"
        }, "timestamp": ts()},
    ],

    "safety": [
        {"type": "perception_result", "data": {
            "objects": [
                {"id": "obj_1", "name": "kitchen knife", "position": "center",
                 "estimated_size": "medium", "color": "silver", "material_guess": "metal",
                 "graspable": True, "confidence": 0.88}
            ],
            "scene_description": "A kitchen knife placed on the workspace",
            "workspace_clear": True
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "perceiving",
            "detail": "Detected 1 object: kitchen knife at center (88% confidence)"
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "searching",
            "detail": "Searching for knife safety handling...",
            "tavily_query": "is kitchen knife safe for robotic arm handling"
        }, "timestamp": ts()},
        {"type": "tavily_result", "data": {
            "query": "is kitchen knife safe for robotic arm handling",
            "results": [
                {"title": "Safe Robotic Handling of Sharp Objects",
                 "content": "Sharp objects like knives require extreme caution. Grip the handle only, never the blade. Use firm grip to prevent slipping. Always move slowly.",
                 "url": "https://example.com/sharp-handling"},
                {"title": "Industrial Robot Safety Standards for Cutting Tools",
                 "content": "ISO 10218 requires risk assessment for handling cutting tools. Human approval should be required. Slow movement speeds (< 50mm/s) recommended.",
                 "url": "https://example.com/iso-safety"}
            ]
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "planning",
            "detail": "HIGH RISK detected — knife is a sharp object. Requiring human approval."
        }, "timestamp": ts()},
        {"type": "action_plan", "data": {
            "action_id": "demo_003",
            "reasoning": "This is a kitchen knife — a sharp, potentially dangerous object. Web search confirms ISO safety standards require human approval for handling cutting tools.",
            "risk_level": "high",
            "risk_justification": "Sharp object that could cause injury if dropped or mishandled. ISO 10218 requires risk assessment.",
            "actions": [
                {"step": 1, "action": "move_to", "target": "center", "description": "Approach knife handle carefully"},
                {"step": 2, "action": "grasp", "force": "firm", "description": "Grip handle firmly to prevent slipping"},
                {"step": 3, "action": "move_to", "target": "above", "description": "Lift slowly"},
                {"step": 4, "action": "pause", "description": "Hold steady for handoff"}
            ],
            "requires_approval": True
        }, "timestamp": ts()},
    ],

    "sort": [
        {"type": "perception_result", "data": {
            "objects": [
                {"id": "obj_1", "name": "ballpoint pen", "position": "center-right",
                 "estimated_size": "small", "color": "blue", "material_guess": "plastic",
                 "graspable": True, "confidence": 0.95},
                {"id": "obj_2", "name": "red apple", "position": "center",
                 "estimated_size": "medium", "color": "red", "material_guess": "organic",
                 "graspable": True, "confidence": 0.91},
                {"id": "obj_3", "name": "paperback book", "position": "center-left",
                 "estimated_size": "large", "color": "white", "material_guess": "paper",
                 "graspable": True, "confidence": 0.89}
            ],
            "scene_description": "Three objects on desk: pen, apple, and book",
            "workspace_clear": True
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "perceiving",
            "detail": "Detected 3 objects: ballpoint pen, red apple, paperback book"
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "searching",
            "detail": "Searching for object weights to determine sort order...",
            "tavily_query": "ballpoint pen average weight grams"
        }, "timestamp": ts()},
        {"type": "tavily_result", "data": {
            "query": "ballpoint pen average weight grams",
            "results": [
                {"title": "Average Pen Weight",
                 "content": "A standard ballpoint pen weighs approximately 10-15 grams.",
                 "url": "https://example.com/pen-weight"}
            ]
        }, "timestamp": ts()},
        {"type": "tavily_result", "data": {
            "query": "apple weight grams",
            "results": [
                {"title": "Apple Weight Guide",
                 "content": "A medium apple weighs approximately 180-200 grams.",
                 "url": "https://example.com/apple-weight"}
            ]
        }, "timestamp": ts()},
        {"type": "tavily_result", "data": {
            "query": "paperback book weight grams",
            "results": [
                {"title": "Book Weight Reference",
                 "content": "A standard paperback book weighs 200-400 grams depending on page count.",
                 "url": "https://example.com/book-weight"}
            ]
        }, "timestamp": ts()},
        {"type": "reasoning_step", "data": {
            "step": "planning",
            "detail": "Sort order determined: pen (12g) → apple (190g) → book (300g). Planning pick-and-place sequence."
        }, "timestamp": ts()},
        {"type": "action_plan", "data": {
            "action_id": "demo_002",
            "reasoning": "Based on Tavily weight data: pen ~12g, apple ~190g, book ~300g. Will rearrange left-to-right by ascending weight.",
            "risk_level": "low",
            "risk_justification": "Common household objects, none fragile or dangerous",
            "actions": [
                {"step": 1, "action": "move_to", "target": "center-right", "description": "Go to pen"},
                {"step": 2, "action": "grasp", "force": "gentle", "description": "Pick up pen"},
                {"step": 3, "action": "move_to", "target": "far-left", "description": "Place pen at far-left (lightest)"},
                {"step": 4, "action": "release", "description": "Release pen"},
                {"step": 5, "action": "move_to", "target": "center", "description": "Go to apple"},
                {"step": 6, "action": "grasp", "force": "normal", "description": "Pick up apple"},
                {"step": 7, "action": "move_to", "target": "center-left", "description": "Place at center-left"},
                {"step": 8, "action": "release", "description": "Release apple"}
            ],
            "requires_approval": False
        }, "timestamp": ts()},
    ],
}


async def run_scenario(name: str):
    if name not in SCENARIOS:
        print(f"Unknown scenario: {name}. Available: {', '.join(SCENARIOS.keys())}")
        return

    print(f"Running scenario: {name}")
    async with websockets.connect(WS_URL) as ws:
        for event in SCENARIOS[name]:
            event["timestamp"] = ts()
            print(f"  Sending: {event['type']}")
            await ws.send(json.dumps(event))
            await asyncio.sleep(1.5)

    print(f"Scenario '{name}' complete!")


async def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"

    if scenario == "all":
        for name in SCENARIOS:
            await run_scenario(name)
            await asyncio.sleep(3)
    else:
        await run_scenario(scenario)


if __name__ == "__main__":
    asyncio.run(main())
