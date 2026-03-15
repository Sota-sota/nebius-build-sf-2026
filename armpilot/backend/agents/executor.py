"""
Executor — sends joint waypoints to the SO101 arm via LeRobot.
Falls back to DummyExecutor when arm is not connected.
"""

import asyncio
import os
from config import ARM_PORT, ARM_ID, POSITION_MAP, STEP_DELAY_S, INTERPOLATION_STEPS, JOINT_LIMITS
from models.action import ActionPlan

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def pos_list_to_action(pos: list) -> dict:
    """[v0, v1, ..., v5] -> {"shoulder_pan.pos": v0, ..., "gripper.pos": v5}"""
    return {f"{name}.pos": val for name, val in zip(MOTOR_NAMES, pos)}


def interpolate(start: list, end: list, steps: int) -> list[list[float]]:
    """Generate intermediate waypoints between start and end positions."""
    return [
        [start[j] + (end[j] - start[j]) * i / steps for j in range(len(start))]
        for i in range(1, steps + 1)
    ]


def clamp_to_limits(pos: list) -> list:
    """Clamp joint positions to safe limits."""
    return [
        max(JOINT_LIMITS["min"][i], min(JOINT_LIMITS["max"][i], v))
        for i, v in enumerate(pos)
    ]


class ArmExecutor:
    def __init__(self):
        from lerobot.robots import make_robot_from_config
        from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

        config = SOFollowerRobotConfig(port=ARM_PORT, id=ARM_ID)
        self.robot = make_robot_from_config(config)
        self.robot.connect()
        self.current = [0.0] * 6

    async def execute(self, waypoints: list, plan: ActionPlan, broadcast_fn):
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "executing", "detail": "Executing on SO101 arm..."},
        })
        valid = [w for w in waypoints if w is not None]
        total = len(valid)
        done = 0

        try:
            for wp in waypoints:
                if wp is None:
                    await asyncio.sleep(1.0)
                    continue

                wp = clamp_to_limits(wp)
                for interp in interpolate(self.current, wp, INTERPOLATION_STEPS):
                    interp = clamp_to_limits(interp)
                    await asyncio.to_thread(
                        self.robot.send_action, pos_list_to_action(interp)
                    )
                    await asyncio.sleep(STEP_DELAY_S / INTERPOLATION_STEPS)

                self.current = wp
                done += 1
                await broadcast_fn({
                    "type": "execution_update",
                    "data": {
                        "current_step": done,
                        "total_steps": total,
                        "joint_positions": self.current,
                        "gripper_state": "closed" if self.current[5] > 0.1 else "open",
                        "status": "executing",
                    },
                })

            await broadcast_fn({
                "type": "execution_update",
                "data": {
                    "current_step": total,
                    "total_steps": total,
                    "joint_positions": self.current,
                    "gripper_state": "open",
                    "status": "completed",
                },
            })
        except Exception as e:
            await broadcast_fn({
                "type": "execution_update",
                "data": {
                    "current_step": done,
                    "total_steps": total,
                    "joint_positions": self.current,
                    "gripper_state": "open",
                    "status": "failed",
                },
            })
            await broadcast_fn({
                "type": "error",
                "data": {"message": f"Arm execution failed: {e}", "recoverable": True},
            })
            # Attempt to return home safely
            await self.home()

    async def home(self):
        """Return arm to home position."""
        try:
            home_pos = list(POSITION_MAP["home"])
            for interp in interpolate(self.current, home_pos, INTERPOLATION_STEPS * 2):
                await asyncio.to_thread(
                    self.robot.send_action, pos_list_to_action(interp)
                )
                await asyncio.sleep(STEP_DELAY_S / INTERPOLATION_STEPS)
            self.current = home_pos
        except Exception:
            pass

    def get_status(self) -> dict:
        """Return current joint positions."""
        return {
            "joint_positions": self.current,
            "gripper_state": "closed" if self.current[5] > 0.1 else "open",
        }

    def disconnect(self):
        self.robot.disconnect()


class DummyExecutor:
    """Fallback when SO101 arm is not connected — simulates arm movement."""

    def __init__(self):
        self.current = [0.0] * 6

    async def execute(self, waypoints: list, plan: ActionPlan, broadcast_fn):
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "executing", "detail": "[Simulation] Executing arm movement..."},
        })
        valid = [w for w in waypoints if w is not None]
        total = len(valid)

        for i, wp in enumerate(valid):
            # Simulate interpolation delay
            for interp in interpolate(self.current, wp, INTERPOLATION_STEPS):
                self.current = interp
                await asyncio.sleep(STEP_DELAY_S / INTERPOLATION_STEPS)

            self.current = wp
            await broadcast_fn({
                "type": "execution_update",
                "data": {
                    "current_step": i + 1,
                    "total_steps": total,
                    "joint_positions": wp,
                    "gripper_state": "closed" if wp[5] > 0.1 else "open",
                    "status": "executing",
                },
            })

        await broadcast_fn({
            "type": "execution_update",
            "data": {
                "current_step": total,
                "total_steps": total,
                "joint_positions": self.current,
                "gripper_state": "open",
                "status": "completed",
            },
        })

    def get_status(self) -> dict:
        return {
            "joint_positions": self.current,
            "gripper_state": "closed" if self.current[5] > 0.1 else "open",
        }


def get_executor():
    if os.path.exists(ARM_PORT):
        try:
            return ArmExecutor()
        except Exception as e:
            print(f"[WARNING] ArmExecutor failed ({e}). Using DummyExecutor.")
    else:
        print(f"[WARNING] {ARM_PORT} not found. Using DummyExecutor.")
    return DummyExecutor()
