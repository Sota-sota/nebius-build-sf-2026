"""
Reasoning agent — takes user command + scene + Tavily context,
generates an ActionPlan via Nebius LLM.
"""

import json
import asyncio
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_MODEL
from models.action import ActionPlan
from tools.tavily_search import TavilySearchTool
from tools.toloka_homer import get_homer_context

SYSTEM_PROMPT = """You are ArmPilot, an AI reasoning agent controlling a 6-DOF SO101 robotic arm (5-DOF body + 1-DOF gripper).

## Your capabilities:
- Move to predefined positions: far-left, center-left, center, center-right, far-right, above
- Grasp objects with the gripper (force: gentle, normal, firm)
- Release objects
- You have a reach radius of ~30cm from the base

## Your process:
1. Analyze the user's command and the current scene
2. Identify which objects are involved
3. Use Tavily web search results to ground your decisions:
   - Object properties (weight, fragility, material behavior)
   - Safe handling approaches
   - Task-specific knowledge (e.g., recipe order, sorting criteria)
4. Plan a sequence of discrete actions
5. Assess risk level:
   - LOW: common objects, simple movements, no fragility concerns
   - MEDIUM: fragile objects, complex multi-step tasks
   - HIGH: potentially dangerous objects, uncertain identification, heavy items

## Output format (ONLY valid JSON, no markdown):
{
    "reasoning": "Step by step explanation of your thinking...",
    "tavily_queries_used": ["query1", "query2"],
    "knowledge_summary": "Key findings from web search that informed my plan...",
    "risk_level": "low",
    "risk_justification": "Why this risk level...",
    "actions": [
        {
            "step": 1,
            "action": "move_to",
            "target": "center-left",
            "description": "Approach the red mug"
        },
        {
            "step": 2,
            "action": "grasp",
            "force": "gentle",
            "description": "Grip the ceramic mug gently to avoid breakage"
        },
        {
            "step": 3,
            "action": "move_to",
            "target": "far-left",
            "description": "Transport mug to the left position"
        },
        {
            "step": 4,
            "action": "release",
            "description": "Place the mug down carefully"
        }
    ],
    "requires_approval": false
}

## Rules:
- ALWAYS reference Tavily search findings in your reasoning
- NEVER skip the knowledge grounding step
- If uncertain about an object, set risk_level to "high"
- Maximum 8 actions per plan
- Each action must be one of: move_to, grasp, release, pause
- requires_approval must be true if risk_level is not "low"
"""


class ReasoningAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1",
            api_key=NEBIUS_API_KEY,
        )
        self.tavily = TavilySearchTool()

    async def reason(self, command: str, scene: dict, broadcast_fn) -> ActionPlan:
        # Step 1: Tavily search
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "searching", "detail": "Running Tavily searches..."},
        })
        objects = [o["name"] for o in scene.get("objects", [])]
        context = await self.tavily.search_for_command(objects, command, broadcast_fn)

        # Step 2: Enrich with Toloka HomER egocentric demonstrations
        homer_context = await get_homer_context(command, objects)
        if homer_context:
            await broadcast_fn({
                "type": "homer_result",
                "data": {"demos": homer_context, "source": "toloka/HomER"},
            })

        # Step 3: LLM reasoning
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "planning", "detail": "Generating action plan with Nebius LLM..."},
        })

        homer_section = f"\nEgocentric demos (Toloka HomER):\n{homer_context}" if homer_context else ""
        user_msg = (
            f"Command: {command}\n"
            f"Scene: {json.dumps(scene)}\n"
            f"Web knowledge:\n{context}"
            f"{homer_section}"
        )

        response = await asyncio.to_thread(
            lambda: self.client.chat.completions.create(
                model=NEBIUS_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
        )

        raw = response.choices[0].message.content.strip()
        data = _parse_json(raw)

        # Retry once on parse failure with simpler prompt
        if data is None:
            retry_response = await asyncio.to_thread(
                lambda: self.client.chat.completions.create(
                    model=NEBIUS_MODEL,
                    messages=[
                        {"role": "system", "content": "Return ONLY valid JSON, no markdown. " + SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=1500,
                )
            )
            raw = retry_response.choices[0].message.content.strip()
            data = _parse_json(raw)
            if data is None:
                raise ValueError(f"LLM returned unparseable response: {raw[:200]}")

        plan = ActionPlan(**data)

        await broadcast_fn({"type": "action_plan", "data": plan.model_dump()})

        if plan.requires_approval:
            await broadcast_fn({
                "type": "reasoning_step",
                "data": {
                    "step": "awaiting_approval",
                    "detail": f"Risk={plan.risk_level}. Waiting for human approval.",
                },
            })

        return plan


def _parse_json(raw: str) -> dict | None:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        # Extract content between first pair of ```
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
