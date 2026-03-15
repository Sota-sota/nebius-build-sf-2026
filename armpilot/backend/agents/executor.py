import asyncio
import os
from config import ARM_PORT, ARM_ID, POSITION_MAP
from models.action import ActionPlan

STEP_DELAY_S        = 0.3
INTERPOLATION_STEPS = 5

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def pos_list_to_action(pos: list) -> dict:
    """[v0, v1, ..., v5] → {"shoulder_pan.pos": v0, ..., "gripper.pos": v5}"""
    return {f"{name}.pos": val for name, val in zip(MOTOR_NAMES, pos)}


def interpolate(start: list, end: list, steps: int) -> list:
    return [
        [start[j] + (end[j] - start[j]) * i / steps for j in range(len(start))]
        for i in range(1, steps + 1)
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
        for wp in waypoints:
            if wp is None:
                await asyncio.sleep(1.0)
                continue
            for interp in interpolate(self.current, wp, INTERPOLATION_STEPS):
                await asyncio.to_thread(self.robot.send_action, pos_list_to_action(interp))
                await asyncio.sleep(STEP_DELAY_S / INTERPOLATION_STEPS)
            self.current = wp
            done += 1
            await broadcast_fn({
                "type": "execution_update",
                "data": {
                    "current_step": done,
                    "total_steps": total,
                    "joint_positions": self.current[:5],
                    "gripper_state": "closed" if self.current[5] > 0.1 else "open",
                    "status": "executing",
                },
            })
        await broadcast_fn({
            "type": "execution_update",
            "data": {
                "current_step": total,
                "total_steps": total,
                "joint_positions": self.current[:5],
                "gripper_state": "open",
                "status": "completed",
            },
        })

    async def home(self):
        home_pos = list(POSITION_MAP["home"])
        await asyncio.to_thread(self.robot.send_action, pos_list_to_action(home_pos))

    def disconnect(self):
        self.robot.disconnect()


class DummyExecutor:
    """アーム未接続時のフォールバック — broadcast だけ行う"""

    def __init__(self):
        self.current = [0.0] * 6

    async def execute(self, waypoints: list, plan: ActionPlan, broadcast_fn):
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "executing", "detail": "[DummyExecutor] Simulating arm movement..."},
        })
        valid = [w for w in waypoints if w is not None]
        total = len(valid)
        for i, wp in enumerate(valid):
            await asyncio.sleep(0.5)
            self.current = wp
            await broadcast_fn({
                "type": "execution_update",
                "data": {
                    "current_step": i + 1,
                    "total_steps": total,
                    "joint_positions": wp[:5],
                    "gripper_state": "closed" if wp[5] > 0.1 else "open",
                    "status": "executing",
                },
            })
        await broadcast_fn({
            "type": "execution_update",
            "data": {"current_step": total, "total_steps": total, "status": "completed"},
        })


def get_executor():
    if os.path.exists(ARM_PORT):
        try:
            return ArmExecutor()
        except Exception as e:
            print(f"[WARNING] ArmExecutor failed ({e}). Using DummyExecutor.")
    else:
        print(f"[WARNING] {ARM_PORT} not found. Using DummyExecutor.")
    return DummyExecutor()
