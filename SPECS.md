# ArmPilot — Complete Technical Specification

## Project Summary

ArmPilot is a voice-controlled SO101 robotic arm system powered by an LLM-based agentic pipeline. The user speaks a natural language command, a reasoning agent uses Tavily web search to ground its decisions in real-time knowledge, plans a sequence of physical actions, and executes them on the SO101 arm — all while streaming every decision to a live Mission Control dashboard.

**Hackathon**: Nebius Build SF, March 15, 2026
**Problem Statement**: Statement 1 — Edge Inference & Agents
**Team Size**: Up to 4

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)               │
│                                                         │
│  ┌──────────┐ ┌───────────────┐ ┌────────────────────┐  │
│  │ Voice    │ │ Camera Feed   │ │ Reasoning Trace    │  │
│  │ Input    │ │ + Scene JSON  │ │ (Agent Prism-like) │  │
│  └──────────┘ └───────────────┘ └────────────────────┘  │
│  ┌──────────┐ ┌───────────────┐ ┌────────────────────┐  │
│  │ Arm      │ │ Tavily Search │ │ Approval Gate      │  │
│  │ Status   │ │ Results       │ │ (risk-based)       │  │
│  └──────────┘ └───────────────┘ └────────────────────┘  │
│                                                         │
│  WebSocket ←──────────────────────────────────→ Backend  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)              │
│                                                         │
│  main.py ── WebSocket Hub ── Event Bus                  │
│      │                                                  │
│      ├── agents/perception.py    Camera → VLM → JSON    │
│      ├── agents/reasoning.py     LLM + Tavily → Plan    │
│      ├── agents/planner.py       Plan → Joint Waypoints │
│      └── agents/executor.py      Waypoints → LeRobot    │
│                                                         │
│  tools/                                                 │
│      ├── tavily_search.py        Tavily SDK wrapper     │
│      └── vision.py               VLM API calls          │
│                                                         │
│  config.py ── API keys, model IDs, arm config           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  HARDWARE                                │
│  SO101 Follower Arm (6-DOF, STS3215 servos)            │
│  USB Camera (wrist-mounted or external)                 │
│  Connected via USB-C to laptop                          │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Package Manager | uv | latest |
| Backend Runtime | Python | 3.11+ |
| Backend Framework | FastAPI | 0.115+ |
| WebSocket | fastapi + websockets | — |
| Robot Control | lerobot | latest |
| LLM Inference | openai SDK (OpenAI-compatible) | 1.x |
| Web Search | tavily-python | latest |
| Frontend | React 18 + Vite | 5.x |
| UI Components | shadcn/ui | latest |
| Styling | Tailwind CSS | 3.x |
| State Management | Zustand | 4.x |
| Icons | Lucide React | latest |
| Voice | Web Speech API (browser-native) | — |

---

## External APIs

### Nebius Token Factory (Primary LLM)
- **Base URL**: `https://api.tokenfactory.nebius.com/v1`
- **Auth**: Bearer token via `NEBIUS_API_KEY`
- **Models**:
  - Reasoning: `meta-llama/Llama-3.3-70B-Instruct` (primary) or `Qwen/Qwen3-30B-A3B`
  - Vision: check availability, fallback to OpenRouter
- **SDK**: OpenAI-compatible (`from openai import OpenAI`)
- **Rate limit**: Use credits from hackathon promo code

### Tavily (Web Search — COMPULSORY)
- **SDK**: `tavily-python`
- **Auth**: `TAVILY_API_KEY`
- **Endpoints used**:
  - `client.search(query, search_depth="basic", max_results=3)` — fast search
  - `client.get_search_context(query)` — returns context string for RAG
- **Usage pattern**: Agent calls Tavily BEFORE every action decision. Searches for object properties, safety info, task context.

### OpenRouter (Fallback + Vision)
- **Base URL**: `https://openrouter.ai/api/v1`
- **Auth**: Bearer token via `OPENROUTER_API_KEY`
- **Models**:
  - Vision: `qwen/qwen2.5-vl-72b-instruct`
  - Text fallback: `meta-llama/llama-3.3-70b-instruct`
- **Credits**: $20 via code `OR-NEBIUSBUILD-MAR15`

### Hugging Face
- **Usage**: LeRobot library for SO101 arm control
- **Org**: `nebius-build-sf-2026-03` (push final model/dataset here)

---

## Directory Structure

```
armpilot/
├── SPECS.md                        # This file
├── SKILLS.md                       # Claude Code skill file
├── README.md                       # Project README for GitHub
├── .env.example                    # Environment variable template
├── backend/
│   ├── main.py                     # FastAPI app + WebSocket hub
│   ├── config.py                   # Settings, API keys, constants
│   ├── requirements.txt            # Python dependencies
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── perception.py           # Camera → VLM → scene JSON
│   │   ├── reasoning.py            # LLM agent + Tavily integration
│   │   ├── planner.py              # Action plan → joint waypoints
│   │   └── executor.py             # Waypoints → LeRobot commands
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tavily_search.py        # Tavily SDK wrapper + caching
│   │   └── vision.py               # VLM API calls (Nebius/OpenRouter)
│   └── models/
│       ├── __init__.py
│       ├── scene.py                # Pydantic models for scene data
│       ├── action.py               # Pydantic models for action plans
│       └── events.py               # WebSocket event schemas
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx                # React entry point
│   │   ├── App.jsx                 # Root layout with sidebar
│   │   ├── lib/
│   │   │   └── utils.js            # cn() helper, etc.
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js     # WS connection + reconnect
│   │   │   └── useVoice.js         # Web Speech API hook
│   │   ├── stores/
│   │   │   └── appStore.js         # Zustand store for global state
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx     # Collapsible nav sidebar
│   │   │   │   ├── Header.jsx      # Top bar with status
│   │   │   │   └── DashboardLayout.jsx  # Grid layout wrapper
│   │   │   ├── panels/
│   │   │   │   ├── CameraFeed.jsx       # Live camera stream
│   │   │   │   ├── SceneViewer.jsx      # Parsed scene JSON display
│   │   │   │   ├── ReasoningTrace.jsx   # Agent reasoning chain
│   │   │   │   ├── TavilyResults.jsx    # Search results panel
│   │   │   │   ├── ArmStatus.jsx        # Joint positions + gripper
│   │   │   │   └── ApprovalGate.jsx     # Human-in-the-loop confirm
│   │   │   ├── voice/
│   │   │   │   ├── VoiceButton.jsx      # Mic button + waveform
│   │   │   │   └── CommandHistory.jsx   # Recent commands list
│   │   │   └── ui/                      # shadcn/ui components
│   │   │       ├── button.jsx
│   │   │       ├── card.jsx
│   │   │       ├── badge.jsx
│   │   │       ├── scroll-area.jsx
│   │   │       ├── separator.jsx
│   │   │       ├── tooltip.jsx
│   │   │       └── alert.jsx
│   │   └── styles/
│   │       └── globals.css         # Tailwind base + shadcn vars
│   └── public/
│       └── armpilot-logo.svg       # Logo
└── scripts/
    ├── calibrate_arm.py            # SO101 calibration helper
    ├── test_tavily.py              # Quick Tavily API test
    ├── test_nebius.py              # Quick Nebius API test
    └── demo_scenarios.py           # Pre-scripted demo commands
```

---

## Backend Specification

### main.py — FastAPI + WebSocket Hub

```python
# Endpoints:
# GET  /                    → health check
# GET  /api/status          → system status (arm connected, APIs ready)
# WS   /ws                  → main WebSocket for all real-time comms

# WebSocket Message Protocol (JSON):
# Client → Server:
{
    "type": "command",          # User voice/text command
    "text": "pick up the red cup"
}
{
    "type": "approve",          # Human approves pending action
    "action_id": "abc123"
}
{
    "type": "reject",           # Human rejects pending action
    "action_id": "abc123"
}
{
    "type": "capture_scene"     # Trigger perception manually
}

# Server → Client:
{
    "type": "perception_result",
    "data": { "objects": [...], "scene_description": "..." },
    "timestamp": "...",
    "latency_ms": 1200
}
{
    "type": "reasoning_step",
    "data": {
        "step": "searching",    # "perceiving" | "searching" | "planning" | "awaiting_approval" | "executing"
        "detail": "Searching for ceramic mug grip safety...",
        "tavily_query": "ceramic mug safe robotic grip force"
    },
    "timestamp": "..."
}
{
    "type": "tavily_result",
    "data": {
        "query": "ceramic mug safe robotic grip force",
        "results": [
            {"title": "...", "content": "...", "url": "..."}
        ]
    },
    "timestamp": "..."
}
{
    "type": "action_plan",
    "data": {
        "action_id": "abc123",
        "reasoning": "The object is a ceramic mug...",
        "risk_level": "low",      # "low" | "medium" | "high"
        "actions": [
            {"step": 1, "action": "move_to", "target": "object_center", "description": "Approach mug"},
            {"step": 2, "action": "grasp", "force": "gentle", "description": "Grip with care"},
            {"step": 3, "action": "move_to", "target": "left", "description": "Move to left position"},
            {"step": 4, "action": "release", "description": "Place gently"}
        ],
        "requires_approval": false
    },
    "timestamp": "..."
}
{
    "type": "execution_update",
    "data": {
        "current_step": 2,
        "total_steps": 4,
        "joint_positions": [0.1, -0.5, 0.3, 0.0, 0.1, 0.8],
        "gripper_state": "closing",
        "status": "executing"     # "executing" | "completed" | "failed"
    },
    "timestamp": "..."
}
{
    "type": "camera_frame",
    "data": {
        "frame_b64": "...",       # base64-encoded JPEG
        "width": 640,
        "height": 480
    }
}
{
    "type": "error",
    "data": {
        "message": "VLM request timed out",
        "recoverable": true
    }
}
```

### agents/perception.py

```python
# Input:  Raw camera frame (captured via OpenCV)
# Output: SceneDescription (Pydantic model)

# Flow:
# 1. Capture frame from USB camera via cv2.VideoCapture
# 2. Encode as JPEG → base64
# 3. Send to VLM (Nebius Token Factory or OpenRouter) with structured prompt
# 4. Parse JSON response into SceneDescription
# 5. Broadcast via WebSocket

# VLM Prompt:
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

# Camera settings:
CAMERA_INDEX = 0        # USB camera index
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CAPTURE_INTERVAL = 2.0  # seconds between auto-captures
```

### agents/reasoning.py

```python
# Input:  User command (str) + SceneDescription + optional previous context
# Output: ActionPlan (Pydantic model)

# Flow:
# 1. Receive user command
# 2. Get latest scene from perception
# 3. Determine what Tavily searches are needed
# 4. Execute Tavily searches (broadcast results to frontend)
# 5. Combine: command + scene + Tavily findings
# 6. Call Nebius LLM to generate action plan
# 7. Assess risk level
# 8. If risk=high → require human approval
# 9. Return ActionPlan

REASONING_SYSTEM_PROMPT = """You are ArmPilot, an AI reasoning agent controlling a 6-DOF SO101 robotic arm (5-DOF body + 1-DOF gripper).

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
    ]
}

## Rules:
- ALWAYS reference Tavily search findings in your reasoning
- NEVER skip the knowledge grounding step
- If uncertain about an object, set risk_level to "high"
- Maximum 8 actions per plan
- Each action must be one of: move_to, grasp, release, pause
"""

# Tavily integration pattern:
# For each command, generate 2-3 targeted search queries:
# 1. Object-specific: "{object_name} properties weight fragility"
# 2. Task-specific: "robot arm {task_verb} {object_type} best practice"
# 3. Safety: "is {object_name} safe to grip robotically"
```

### agents/planner.py

```python
# Input:  ActionPlan (from reasoning agent)
# Output: List of joint waypoints (6 floats each)

# Predefined position map (calibrate these with the actual arm):
POSITION_MAP = {
    "home":         [0.0,   0.0,   0.0,   0.0,   0.0,   0.0],
    "far-left":     [-1.2, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-left":  [-0.6, -0.4,   0.5,   0.0,   0.0,   0.0],
    "center":       [0.0,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "center-right": [0.6,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "far-right":    [1.2,  -0.4,   0.5,   0.0,   0.0,   0.0],
    "above":        [0.0,  -0.2,   0.3,   0.0,   0.0,   0.0],
}

GRIPPER_OPEN  = 0.0
GRIPPER_CLOSED_GENTLE = 0.5
GRIPPER_CLOSED_NORMAL = 0.75
GRIPPER_CLOSED_FIRM   = 1.0

# NOTE: These values are PLACEHOLDERS. Must be calibrated with the
# actual arm on the day. The hardware teammate should update these
# values in the first hour after calibration.

# Motion parameters:
STEP_DELAY_S = 0.3          # Delay between waypoint steps
INTERPOLATION_STEPS = 5     # Intermediate steps for smooth motion
```

### agents/executor.py

```python
# Input:  List of joint waypoints
# Output: Execution status (broadcasts updates to frontend)

# Flow:
# 1. Connect to SO101 via LeRobot
# 2. For each waypoint:
#    a. Interpolate from current position to target (INTERPOLATION_STEPS)
#    b. Send each intermediate position via robot.send_action()
#    c. Wait STEP_DELAY_S between steps
#    d. Broadcast execution_update to frontend
# 3. Report completion or failure

# LeRobot setup:
# from lerobot.common.robot_devices.robots.factory import make_robot
# robot = make_robot("so101_follower", port=ARM_PORT, id="armpilot")

# Safety: If any joint position exceeds limits, abort immediately
JOINT_LIMITS = {
    "min": [-2.0, -2.0, -2.0, -2.0, -2.0, 0.0],
    "max": [2.0,   2.0,  2.0,  2.0,  2.0, 1.0],
}
```

### tools/tavily_search.py

```python
# Wrapper around Tavily SDK with:
# 1. Response caching (in-memory dict, keyed by query)
# 2. Rate limiting (max 3 queries per command)
# 3. Error handling with graceful fallback
# 4. Result formatting for LLM consumption

# Cache: simple dict, cleared every 100 entries
# Timeout: 5 seconds per search
# Fallback: if Tavily fails, return "No web search results available. Proceed with caution."
```

### models/ — Pydantic Schemas

```python
# scene.py
class DetectedObject(BaseModel):
    id: str
    name: str
    position: Literal["far-left", "center-left", "center", "center-right", "far-right"]
    estimated_size: Literal["tiny", "small", "medium", "large"]
    color: str
    material_guess: str
    graspable: bool
    confidence: float

class SceneDescription(BaseModel):
    objects: list[DetectedObject]
    scene_description: str
    workspace_clear: bool
    timestamp: datetime

# action.py
class ActionStep(BaseModel):
    step: int
    action: Literal["move_to", "grasp", "release", "pause"]
    target: str | None = None
    force: Literal["gentle", "normal", "firm"] | None = None
    description: str

class ActionPlan(BaseModel):
    action_id: str                    # UUID
    reasoning: str
    tavily_queries_used: list[str]
    knowledge_summary: str
    risk_level: Literal["low", "medium", "high"]
    risk_justification: str
    actions: list[ActionStep]
    requires_approval: bool           # True if risk_level != "low"

# events.py — All WebSocket event types with Pydantic validation
```

---

## Frontend Specification

### Dashboard Layout (CSS Grid)

```
┌──────────────────────────────────────────────────────────────┐
│  Header: "ArmPilot Mission Control"  [Status: ● Connected]  │
├────────┬─────────────────────┬───────────────────────────────┤
│        │                     │                               │
│  Side  │   Camera Feed       │   Reasoning Trace             │
│  bar   │   (live stream)     │   (scrolling timeline)        │
│        │                     │                               │
│  Nav   │   ┌─────────────┐   │   ┌─ Step 1: Perceiving ──┐  │
│        │   │  640 x 480  │   │   │  Detected: red mug    │  │
│  •Dash │   │  video feed │   │   ├─ Step 2: Searching ───┤  │
│  •Logs │   │             │   │   │  Tavily: "ceramic..."  │  │
│  •Cfg  │   └─────────────┘   │   ├─ Step 3: Planning ────┤  │
│        │                     │   │  4 actions planned     │  │
│        │   Scene JSON        │   └────────────────────────┘  │
│        │   (object cards)    │                               │
├────────┼─────────────────────┼───────────────────────────────┤
│        │                     │                               │
│        │   Arm Status        │   Tavily Search Results       │
│        │   ┌──────────────┐  │   ┌────────────────────────┐  │
│        │   │ J1: 0.34 rad │  │   │ Q: "ceramic mug grip"  │  │
│        │   │ J2: -0.52    │  │   │ → Result 1: ...        │  │
│        │   │ Grip: OPEN   │  │   │ → Result 2: ...        │  │
│        │   └──────────────┘  │   └────────────────────────┘  │
├────────┴─────────────────────┴───────────────────────────────┤
│                                                              │
│  🎤 [  Hold to Speak  ]                    [ ⚠ APPROVE  ]  │
│                                                              │
│  Command: "pick up the red cup and move it to the left"      │
└──────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### VoiceButton.jsx
- Big circular mic button, centered bottom bar
- States: idle (gray), listening (pulsing red), processing (spinning)
- Uses Web Speech API (`webkitSpeechRecognition`)
- `interimResults: true` — show live transcription as user speaks
- On final result → send `{type: "command", text}` via WebSocket
- Fallback: text input field for typing commands

#### CameraFeed.jsx
- Displays base64 JPEG frames received via WebSocket `camera_frame` events
- Renders in a `<img>` tag with `src={data:image/jpeg;base64,...}`
- Overlays: object bounding indicators (colored dots at positions matching scene JSON)
- Shows "No camera" placeholder if no frames received in 5s

#### SceneViewer.jsx
- Cards for each detected object
- Card shows: name, color dot, size badge, material, graspable indicator
- Confidence bar (0-100%)
- Updates on each `perception_result` event

#### ReasoningTrace.jsx (inspired by evilmartians/agent-prism)
- Vertical timeline with expandable steps
- Step types: PERCEIVING → SEARCHING → PLANNING → AWAITING_APPROVAL → EXECUTING
- Each step shows:
  - Icon + color-coded badge
  - Timestamp + latency
  - Expandable detail (reasoning text, search queries, action list)
- Auto-scrolls to latest step
- Glowing pulse animation on the current active step

#### TavilyResults.jsx
- Scrollable card list
- Each card: search query (bold), then result cards with title, snippet, URL
- New searches animate in from the right
- Badge showing "X searches this session"

#### ArmStatus.jsx
- 6 horizontal bars for joint positions (J1-J5 + Gripper)
- Color: green = within normal range, yellow = approaching limit, red = at limit
- Gripper state: OPEN / CLOSING / CLOSED (with icon)
- Updates at ~10Hz from execution_update events

#### ApprovalGate.jsx
- Hidden when no pending action
- When risk_level="medium": yellow card with "Review Action" button
- When risk_level="high": red pulsing card with "⚠ DANGER — Approve?" button
- Shows: action summary, risk justification, action count
- Two buttons: "Approve" (green) and "Reject" (red)
- On approve → send `{type: "approve", action_id}` via WebSocket
- On reject → send `{type: "reject", action_id}` via WebSocket

### UI Design Tokens (shadcn + custom)

```css
/* Risk level colors */
--risk-low:    hsl(142 76% 36%);     /* green */
--risk-medium: hsl(38 92% 50%);      /* amber */
--risk-high:   hsl(0 84% 60%);       /* red */

/* Agent step colors */
--step-perceiving: hsl(221 83% 53%); /* blue */
--step-searching:  hsl(25 95% 53%);  /* orange — Tavily brand */
--step-planning:   hsl(262 83% 58%); /* purple */
--step-executing:  hsl(142 76% 36%); /* green */
--step-awaiting:   hsl(38 92% 50%);  /* amber */

/* Font: system default from shadcn is fine for hackathon */
```

### Dashboard Template Source

Fork from `satnaing/shadcn-admin` (Vite + React + shadcn/ui).
- Strip all demo pages (users, settings, tasks, etc.)
- Keep: sidebar layout, dark/light toggle, command menu (Cmd+K)
- Replace content area with the 6 panels above

Reference for specific components:
- Reasoning trace: adapt patterns from `evilmartians/agent-prism`
- Camera streaming: base64 via WebSocket pattern from `ddelago/Real-Time-Robotics-Dashboard`
- Arm telemetry: joint bar visualization from `Relativiteit/ros-robot-control-dashboard`

---

## Environment Variables

```env
# .env
NEBIUS_API_KEY=your_nebius_token_factory_key
NEBIUS_MODEL=meta-llama/Llama-3.3-70B-Instruct
NEBIUS_VISION_MODEL=                              # if available on Nebius

TAVILY_API_KEY=your_tavily_api_key

OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_VISION_MODEL=qwen/qwen2.5-vl-72b-instruct

ARM_PORT=/dev/ttyACM0                             # SO101 follower arm USB port
ARM_ID=armpilot_follower
CAMERA_INDEX=0

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

---

## Demo Scenarios (for judging)

### Demo 1: "The Smart Pick" (30 seconds)
```
Command: "Pick up the ceramic mug carefully"
Expected flow:
1. Perception: identifies "red ceramic mug" at center-left
2. Tavily searches: "ceramic mug fragility", "safe robotic grip force ceramic"
3. Reasoning: risk=low, force=gentle, 4-step plan
4. Execution: arm moves, grasps gently, holds up
Dashboard shows: full trace with Tavily results visible
```

### Demo 2: "Knowledge-Grounded Sorting" (45 seconds)
```
Command: "Sort these objects by weight, lightest to heaviest"
Expected flow:
1. Perception: identifies 3 objects (pen, apple, book)
2. Tavily searches: "pen average weight grams", "apple weight grams", "paperback book weight"
3. Reasoning: pen (10g) → apple (200g) → book (300g), plans pick-place sequence
4. Execution: rearranges objects left-to-right by weight
Dashboard shows: Tavily results with actual weight data informing the ordering
```

### Demo 3: "Safety-First" (45 seconds)
```
Command: "Hand me that object" (knife or glass placed in workspace)
Expected flow:
1. Perception: identifies "kitchen knife" or "glass cup"
2. Tavily searches: "is kitchen knife safe for robotic arm handling"
3. Reasoning: risk=HIGH, requires approval
4. Dashboard: Approval gate activates with red warning
5. Human approves → arm proceeds with extra caution (slow, firm grip)
Dashboard shows: risk escalation, approval gate UI, cautious execution
```

---

## Dependencies

### Python (backend/requirements.txt)
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=12.0
openai>=1.0.0
tavily-python>=0.5.0
opencv-python-headless>=4.9.0
pydantic>=2.0.0
python-dotenv>=1.0.0
lerobot
torch
numpy
```

### Node (frontend/package.json)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^4.5.0",
    "lucide-react": "^0.383.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

## Judging Alignment

| Criteria | Weight | How ArmPilot Scores |
|----------|--------|---------------------|
| Live Demo | 45% | Voice command → visible reasoning → physical robot action. Full transparency via dashboard. |
| Creativity & Originality | 35% | First system bridging LLM reasoning + web knowledge grounding + physical robotics with observability. Nobody else combining Tavily + robot arm. |
| Impact Potential | 20% | "Search before you act" pattern generalizes to warehouses, kitchens, hospitals. Open-source, reproducible. |

---

## Anti-Patterns to AVOID (from hackathon rules)

- ❌ Do NOT make this a chatbot or RAG app
- ❌ Do NOT use Streamlit
- ❌ Do NOT build an "AI advisor" or "AI coach"
- ❌ Do NOT show a slide presentation to judges — show the LIVE DEMO
- ✅ DO show a working technical demo
- ✅ DO use Tavily as a core component (not bolt-on)
- ✅ DO build something that goes beyond basic tool calls
