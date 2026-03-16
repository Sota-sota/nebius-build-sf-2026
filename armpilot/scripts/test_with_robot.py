#!/usr/bin/env python3
"""
Standalone end-to-end test: command → LLM reasoning → (SmolVLA or POSITION_MAP) → SO101 arm
No frontend required. All broadcast events are printed to stdout.

Usage:
    cd armpilot/scripts
    python test_with_robot.py "pick up the red cup"
    python test_with_robot.py  # uses default command
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

# Auto-confirm lerobot calibration prompts (just press ENTER)
import builtins
_real_input = builtins.input
def _auto_input(prompt=""):
    print(prompt, flush=True)
    return ""
builtins.input = _auto_input

COMMAND = sys.argv[1] if len(sys.argv) > 1 else "pick up the red cup"

MOCK_SCENE = {
    "objects": [
        {
            "id": "obj_1",
            "name": "red cup",
            "position": "center",
            "estimated_size": "small",
            "color": "red",
            "material_guess": "ceramic",
            "graspable": True,
            "confidence": 0.9,
        }
    ],
    "scene_description": "A red ceramic cup on the workspace",
    "workspace_clear": True,
}

events = []


async def broadcast(event: dict):
    from datetime import datetime, timezone
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
    events.append(event)
    t = event.get("type", "?")
    data = event.get("data", {})
    if t == "reasoning_step":
        print(f"[{t}] {data.get('step')}: {data.get('detail')}")
    elif t == "action_plan":
        plan = data
        print(f"[{t}] risk={plan.get('risk_level')} requires_approval={plan.get('requires_approval')}")
        for a in plan.get("actions", []):
            print(f"         step {a['step']}: {a['action']} {a.get('target','')} {a.get('force','')} — {a['description']}")
    elif t == "execution_update":
        print(f"[{t}] {data.get('status')} {data.get('current_step','')}/{data.get('total_steps','')} joints={data.get('joint_positions')} gripper={data.get('gripper_state')}")
    elif t == "tavily_result":
        q = data.get("query", "")
        n = len(data.get("results", []))
        print(f"[{t}] '{q}' → {n} results")
    elif t == "error":
        print(f"[ERROR] {data.get('message')}")
    else:
        print(f"[{t}] {json.dumps(data)[:120]}")


async def main():
    from agents.reasoning import ReasoningAgent
    from agents.planner import ActionPlanner, actions_to_instruction
    from agents.executor import get_executor
    from agents.smolvla_client import SmolVLAClient
    import config

    print(f"=== ArmPilot robot test ===")
    print(f"Command : {COMMAND!r}")
    print(f"ARM_PORT: {config.ARM_PORT}")
    print(f"USE_SMOLVLA: {config.USE_SMOLVLA}")
    if config.USE_SMOLVLA:
        print(f"SMOLVLA_ENDPOINT_URL: {config.SMOLVLA_ENDPOINT_URL}")
    print()

    # Step 1: LLM reasoning
    agent = ReasoningAgent()
    plan = await agent.reason(COMMAND, MOCK_SCENE, broadcast)

    if plan.requires_approval:
        print(f"\n[APPROVAL REQUIRED] risk={plan.risk_level}")
        print("Auto-approving for test run...")
        # Auto-approve for headless test

    # Step 2: executor (real arm or dummy)
    executor = get_executor()
    executor_type = type(executor).__name__
    print(f"\n[EXECUTOR] {executor_type}")

    # Step 3: SmolVLA or POSITION_MAP
    if config.USE_SMOLVLA:
        instruction = actions_to_instruction(plan)
        print(f"[SmolVLA] instruction: {instruction!r}")
        smolvla = SmolVLAClient()
        current_joints = getattr(executor, "current", [0.0] * 6)
        chunk = await smolvla.predict(instruction, current_joints, None)
        if chunk is not None:
            print(f"[SmolVLA] got chunk: {len(chunk)} steps")
            await executor.execute(chunk, plan, broadcast)
            print("\n=== DONE (SmolVLA path) ===")
            return
        else:
            print("[SmolVLA] FAILED or timed out — falling back to POSITION_MAP")

    planner = ActionPlanner()
    waypoints = planner.plan_to_waypoints(plan)
    print(f"[PLANNER] {len(waypoints)} waypoints")
    await executor.execute(waypoints, plan, broadcast)
    print("\n=== DONE (POSITION_MAP path) ===")


if __name__ == "__main__":
    asyncio.run(main())
