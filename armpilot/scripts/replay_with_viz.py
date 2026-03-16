"""
replay_with_viz.py — Replay a LeRobot dataset on the SO101 arm
while streaming joint positions to the ArmPilot frontend via WebSocket.

Usage:
    python replay_with_viz.py --episode 0
"""

import argparse
import asyncio
import json
import time

import httpx
from datasets import load_dataset

BACKEND_URL = "http://localhost:8000"
REPO_ID = "lerobot/svla_so101_pickplace"
ARM_PORT = "/dev/ttyACM0"
ARM_ID = "armpilot_follower"
FPS = 30

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def load_episode_frames(episode: int):
    """Load joint positions for a single episode from the dataset."""
    ds = load_dataset(REPO_ID, split="train")
    frames = [row for row in ds if row["episode_index"] == episode]
    frames.sort(key=lambda r: r["frame_index"])
    return frames


import math

def frame_to_joints(row) -> list[float]:
    """Extract [j1..j5, gripper] in radians from a dataset row."""
    action = row["action"]  # list of 6 floats in degrees
    # Convert degrees to radians for Three.js; normalize gripper to 0-1
    joints_rad = [math.radians(v) for v in action[:5]]
    gripper_deg = action[5]
    gripper_norm = max(0.0, min(1.0, (gripper_deg + 10) / 110))  # approx -10°..100° → 0..1
    return joints_rad + [gripper_norm]


async def stream_to_frontend(frames: list, client: httpx.AsyncClient):
    """POST execution_update events to backend broadcast endpoint at 30fps."""
    total = len(frames)
    for i, row in enumerate(frames):
        joints = frame_to_joints(row)
        gripper_val = joints[5]
        gripper_state = "closed" if gripper_val > 0.6 else ("closing" if gripper_val > 0.1 else "open")
        event = {
            "type": "execution_update",
            "data": {
                "current_step": i + 1,
                "total_steps": total,
                "joint_positions": joints,
                "gripper_state": gripper_state,
                "status": "executing",
            },
        }
        await client.post(f"{BACKEND_URL}/api/broadcast", json=event)
        await asyncio.sleep(1.0 / FPS)

    await client.post(f"{BACKEND_URL}/api/broadcast", json={
        "type": "execution_update",
        "data": {
            "current_step": total,
            "total_steps": total,
            "joint_positions": frame_to_joints(frames[-1]),
            "gripper_state": "open",
            "status": "completed",
        },
    })


def replay_on_arm(episode: int):
    """Run lerobot-replay as a subprocess (avoids import path conflicts)."""
    import subprocess
    cmd = "/home/saito/miniforge3/envs/lerobot312/bin/lerobot-replay"
    result = subprocess.run([
        cmd,
        "--robot.type=so101_follower",
        f"--robot.port={ARM_PORT}",
        f"--robot.id={ARM_ID}",
        "--dataset.repo_id=lerobot/svla_so101_pickplace",
        f"--dataset.episode={episode}",
    ])
    print(f"[arm] lerobot-replay exited with code {result.returncode}")


async def main(episode: int):
    print(f"Loading episode {episode} from {REPO_ID}...")
    frames = load_episode_frames(episode)
    print(f"Loaded {len(frames)} frames.")

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Announce start
        await client.post(f"{BACKEND_URL}/api/broadcast", json={
            "type": "reasoning_step",
            "data": {
                "step": "executing",
                "detail": f"Replaying dataset episode {episode} ({len(frames)} frames @ {FPS}fps)",
            },
        })

        # Snap 3D arm to episode start position (matches where the physical arm starts)
        start_joints = frame_to_joints(frames[0])
        for _ in range(10):
            await client.post(f"{BACKEND_URL}/api/broadcast", json={
                "type": "execution_update",
                "data": {
                    "current_step": 0,
                    "total_steps": len(frames),
                    "joint_positions": start_joints,
                    "gripper_state": "open",
                    "status": "executing",
                },
            })

        # Run arm replay in thread + stream to frontend concurrently
        loop = asyncio.get_event_loop()
        arm_task = loop.run_in_executor(None, replay_on_arm, episode)
        viz_task = stream_to_frontend(frames, client)

        await asyncio.gather(arm_task, viz_task)
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main(args.episode))
