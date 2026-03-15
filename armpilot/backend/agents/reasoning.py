import json
import asyncio
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_MODEL
from models.action import ActionPlan
from tools.tavily_search import TavilySearchTool

SYSTEM_PROMPT = """You are ArmPilot controlling a 6-DOF SO101 robotic arm.
Positions: far-left, center-left, center, center-right, far-right, above.
Actions: move_to, grasp (force: gentle/normal/firm), release, pause.
Risk: low=common objects, medium=fragile, high=dangerous/uncertain.
requires_approval must be true if risk_level is not "low".
Return ONLY valid JSON, no markdown:
{"reasoning":"...","tavily_queries_used":[],"knowledge_summary":"...","risk_level":"low","risk_justification":"...","actions":[{"step":1,"action":"move_to","target":"center","description":"..."}],"requires_approval":false}"""


class ReasoningAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1",
            api_key=NEBIUS_API_KEY,
        )
        self.tavily = TavilySearchTool()

    async def reason(self, command: str, scene: dict, broadcast_fn) -> ActionPlan:
        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "searching", "detail": "Running Tavily searches..."},
        })
        objects = [o["name"] for o in scene.get("objects", [])]
        context = await self.tavily.search_for_command(objects, command, broadcast_fn)

        await broadcast_fn({
            "type": "reasoning_step",
            "data": {"step": "planning", "detail": "Generating action plan with Nebius LLM..."},
        })
        user_msg = f"Command: {command}\nScene: {json.dumps(scene)}\nWeb knowledge:\n{context}"

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
        # strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
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
