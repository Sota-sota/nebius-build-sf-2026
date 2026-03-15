from config import (
    POSITION_MAP,
    GRIPPER_OPEN,
    GRIPPER_CLOSED_GENTLE,
    GRIPPER_CLOSED_NORMAL,
    GRIPPER_CLOSED_FIRM,
    JOINT_LIMITS,
)
from models.action import ActionPlan

GRIPPER_FORCE_MAP = {
    "gentle": GRIPPER_CLOSED_GENTLE,
    "normal": GRIPPER_CLOSED_NORMAL,
    "firm": GRIPPER_CLOSED_FIRM,
}


class ActionPlanner:
    def __init__(self):
        self.current = [0.0] * 6

    def plan_to_waypoints(self, plan: ActionPlan) -> list:
        waypoints = []
        for step in plan.actions:
            if step.action == "move_to":
                pos = list(POSITION_MAP.get(step.target, POSITION_MAP["center"]))
                pos[5] = self.current[5]  # keep current gripper state
                self._validate(pos)
                waypoints.append(pos)
            elif step.action == "grasp":
                pos = list(self.current)
                pos[5] = GRIPPER_FORCE_MAP.get(step.force or "normal", GRIPPER_CLOSED_NORMAL)
                waypoints.append(pos)
            elif step.action == "release":
                pos = list(self.current)
                pos[5] = GRIPPER_OPEN
                waypoints.append(pos)
            elif step.action == "pause":
                waypoints.append(None)
        return waypoints

    def _validate(self, pos: list):
        for i, v in enumerate(pos):
            lo = JOINT_LIMITS["min"][i]
            hi = JOINT_LIMITS["max"][i]
            if not (lo <= v <= hi):
                raise ValueError(f"Joint {i} value {v:.3f} out of limits [{lo}, {hi}]")


def actions_to_instruction(plan: ActionPlan) -> str:
    """ActionPlan.actions → SmolVLA に渡す自然言語 instruction text に変換する純粋関数"""
    parts = []
    for step in plan.actions:
        if step.action == "move_to" and step.target:
            parts.append(f"move to {step.target}")
        elif step.action == "grasp":
            force = step.force or "normal"
            parts.append(f"grasp {force}ly")
        elif step.action == "release":
            parts.append("release and place down")
        elif step.action == "pause":
            parts.append("pause")
        else:
            parts.append(step.description)
    instruction = ", ".join(parts) if parts else plan.reasoning
    return instruction
