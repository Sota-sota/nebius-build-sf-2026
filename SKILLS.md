---
name: armpilot
description: "Skill for building ArmPilot — a voice-controlled SO101 robotic arm with LLM reasoning, Tavily web search grounding, and a real-time Mission Control dashboard. Use this skill whenever working on any part of the ArmPilot hackathon project, including: backend agents (perception, reasoning, planning, execution), FastAPI WebSocket server, Tavily integration, Nebius Token Factory LLM calls, OpenRouter vision API, LeRobot SO101 arm control, React dashboard frontend, shadcn/ui components, voice input, camera streaming, reasoning trace visualization, approval gate UI, or any feature of the robotic arm control system. Also use when debugging WebSocket connections, calibrating the arm, testing API integrations, or preparing demo scenarios."
---

# ArmPilot — Claude Code Build Skill

## Project Context

ArmPilot is a hackathon project for Nebius Build SF (March 15, 2026). It's a voice-controlled SO101 robotic arm with an LLM-powered agentic pipeline that uses Tavily web search to ground decisions before acting. A real-time Mission Control dashboard shows every reasoning step.

**Read SPECS.md first** — it contains the complete technical specification including architecture, API contracts, WebSocket protocol, Pydantic models, component specs, and demo scenarios. This SKILLS.md provides the BUILD INSTRUCTIONS.

---

## Priority Order

Build in this exact order. Each phase is independently demoable.

### Phase 1: Foundation (Hour 0-1)
### Phase 2: Perception (Hour 1-2)
### Phase 3: Reasoning + Tavily (Hour 2-3)
### Phase 4: Execution + Arm Control (Hour 3-4)
### Phase 5: Dashboard Polish (Hour 4-5)
### Phase 6: Demo Prep + Submission (Hour 5-6)

---

## Phase 1: Foundation

### Backend Setup

```bash
cd armpilot
mkdir -p backend/agents backend/tools backend/models frontend/src scripts
cd backend
uv init
uv add fastapi uvicorn websockets openai tavily-python opencv-python-headless pydantic python-dotenv numpy
```

**Create `backend/config.py` first:**
- Load all env vars from `.env` using `python-dotenv`
- Export constants: `NEBIUS_API_KEY`, `TAVILY_API_KEY`, `OPENROUTER_API_KEY`, `ARM_PORT`, `CAMERA_INDEX`
- Include model name constants
- Include `POSITION_MAP` dict (will be calibrated later)

**Create `backend/main.py`:**
- FastAPI app with CORS middleware (allow all origins for hackathon)
- Single WebSocket endpoint at `/ws`
- Connection manager class that tracks connected clients
- Broadcast helper: `async def broadcast(event: dict)`
- Health check at `GET /`
- Status endpoint at `GET /api/status`

**Test**: Run `uvicorn main:app --reload --host 0.0.0.0 --port 8000`, connect via browser WebSocket console.

### Frontend Setup

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install zustand lucide-react clsx tailwind-merge class-variance-authority
npx tailwindcss init -p
```

**Fork shadcn/ui setup** (from `satnaing/shadcn-admin` patterns):
- Initialize shadcn: `npx shadcn@latest init`
- Add components: `npx shadcn@latest add button card badge scroll-area separator tooltip alert`
- Set up `lib/utils.js` with `cn()` helper

**Create basic layout:**
- `App.jsx` with CSS Grid: sidebar + header + 6-panel content area
- `DashboardLayout.jsx` wrapping the grid
- `Sidebar.jsx` with ArmPilot branding, nav links, dark mode toggle
- `Header.jsx` with connection status indicator

**Create `hooks/useWebSocket.js`:**
- Connect to `ws://localhost:8000/ws`
- Auto-reconnect with exponential backoff
- Parse incoming JSON messages
- Dispatch to Zustand store based on `event.type`
- Expose `sendMessage(data)` function

**Create `stores/appStore.js` (Zustand):**
```javascript
// State shape:
{
    connected: false,
    scene: null,              // latest SceneDescription
    reasoningSteps: [],       // array of reasoning events (timeline)
    tavilyResults: [],        // array of search results
    actionPlan: null,         // current pending ActionPlan
    armStatus: null,          // latest joint positions + gripper
    cameraFrame: null,        // latest base64 frame
    commandHistory: [],       // list of past commands
    pendingApproval: null,    // action awaiting approval
}
```

**Test**: Frontend renders empty dashboard, WebSocket connects to backend, connection status shows green.

### API Verification Scripts

**Create `scripts/test_nebius.py`:**
```python
# Quick test: call Nebius Token Factory, print response
# Confirms API key works and model is available
```

**Create `scripts/test_tavily.py`:**
```python
# Quick test: search "ceramic mug weight", print results
# Confirms Tavily API key works
```

### SO101 Calibration

**Create `scripts/calibrate_arm.py`:**
- Wraps LeRobot calibration commands
- Prints step-by-step instructions
- Records calibrated position values
- Outputs updated `POSITION_MAP` for `planner.py`

**CRITICAL**: Start calibration in parallel with software setup. Hardware teammate runs this while others code.

---

## Phase 2: Perception Pipeline

### Backend

**Create `backend/tools/vision.py`:**
- `async def analyze_frame(frame_b64: str) -> dict`
- Try Nebius Token Factory first (if vision model available)
- Fallback to OpenRouter (`qwen/qwen2.5-vl-72b-instruct`)
- Send base64 image + `PERCEPTION_PROMPT` from SPECS.md
- Parse JSON response, validate with Pydantic
- Retry once on parse failure with simpler prompt
- Timeout: 10 seconds

**Create `backend/agents/perception.py`:**
- `PerceptionAgent` class
- Opens USB camera via `cv2.VideoCapture(CAMERA_INDEX)`
- `async def capture_and_analyze()`:
  1. Read frame from camera
  2. Encode JPEG → base64
  3. Call `vision.analyze_frame()`
  4. Return `SceneDescription` + broadcast to frontend
- `async def stream_camera()`:
  1. Continuous loop, captures frames at 2 FPS
  2. Broadcasts raw frames as `camera_frame` events (low quality JPEG for speed)

**Create `backend/models/scene.py`:**
- Pydantic models as specified in SPECS.md: `DetectedObject`, `SceneDescription`

**Wire into `main.py`:**
- On WebSocket connect, start camera streaming task
- On `capture_scene` message, trigger full perception
- On `command` message, auto-trigger perception before reasoning

### Frontend

**Create `components/panels/CameraFeed.jsx`:**
- Subscribe to `cameraFrame` from Zustand store
- Render `<img src={data:image/jpeg;base64,${frame}} />`
- Aspect ratio container (4:3)
- "No camera" placeholder with camera-off icon
- Subtle fade transition between frames

**Create `components/panels/SceneViewer.jsx`:**
- Subscribe to `scene` from Zustand store
- Map `scene.objects` to cards
- Each card: colored dot (by object color), name, size badge, material tag, confidence bar
- `graspable` shown as green checkmark or red X
- Empty state: "Point camera at workspace"

**Test**: Camera feed appears in dashboard, trigger perception, see scene cards populate.

---

## Phase 3: Reasoning Agent + Tavily

### Backend

**Create `backend/tools/tavily_search.py`:**
- `TavilySearchTool` class
- `__init__`: create `TavilyClient`, init cache dict
- `async def search(query: str) -> dict`:
  1. Check cache (key = query)
  2. If miss: call `tavily_client.search(query, search_depth="basic", max_results=3)`
  3. Format results: `[{title, content[:200], url}]`
  4. Cache result
  5. Return formatted results
- `async def search_for_command(objects: list, task: str) -> str`:
  1. Generate queries:
     - Per object: `"{name} weight material properties"`
     - Per object: `"robotic grip safe handling {material}"`
     - Task: `"robot arm {task} best approach"`
  2. Execute up to 3 queries (rate limit)
  3. Format as context string for LLM
  4. Broadcast each search result to frontend as `tavily_result` event
- Error handling: timeout after 5s, return fallback string

**Create `backend/agents/reasoning.py`:**
- `ReasoningAgent` class
- `__init__`: create OpenAI client (Nebius), create `TavilySearchTool`
- `async def reason(command: str, scene: SceneDescription) -> ActionPlan`:
  1. Broadcast `reasoning_step` (step="perceiving")
  2. Extract object list from scene
  3. Broadcast `reasoning_step` (step="searching")
  4. Call `tavily_tool.search_for_command(objects, command)`
  5. Broadcast `reasoning_step` (step="planning")
  6. Call Nebius LLM with system prompt + user message containing:
     - Command
     - Scene JSON
     - Tavily context string
  7. Parse JSON response into `ActionPlan`
  8. Set `requires_approval = risk_level != "low"`
  9. If requires_approval: broadcast `reasoning_step` (step="awaiting_approval")
  10. Return `ActionPlan`
- `temperature=0.3`, `max_tokens=1500`
- Retry once on JSON parse failure

**Create `backend/models/action.py`:**
- Pydantic models: `ActionStep`, `ActionPlan` as specified in SPECS.md

**Create `backend/models/events.py`:**
- All WebSocket event types as Pydantic models for validation

**Wire into `main.py`:**
- On `command` message:
  1. Run perception (if not recent)
  2. Run reasoning agent
  3. If `requires_approval=false` → proceed to execution
  4. If `requires_approval=true` → wait for approve/reject message
- On `approve` message: proceed to execution
- On `reject` message: broadcast cancellation, return to idle

### Frontend

**Create `components/panels/ReasoningTrace.jsx`:**
- Subscribe to `reasoningSteps` array from Zustand
- Vertical timeline layout (inspired by `agent-prism` TraceViewer)
- Each step is a card with:
  - Left: vertical line with dot (color-coded by step type)
  - Right: step badge, timestamp, expandable detail
- Step badges use `--step-*` color tokens from SPECS.md
- Active step has pulsing animation
- Auto-scrolls to bottom on new step
- Click to expand: shows full reasoning text, search queries, etc.

**Create `components/panels/TavilyResults.jsx`:**
- Subscribe to `tavilyResults` from Zustand
- Each search rendered as:
  - Query text (bold, orange accent — Tavily brand color)
  - Result cards: title, snippet (truncated), URL link
- New results animate in with slide-right + fade
- Badge in header: "X searches"
- Scrollable container

**Create `components/panels/ApprovalGate.jsx`:**
- Subscribe to `pendingApproval` from Zustand
- Hidden when `null`
- When active, slides up from bottom of right panel
- Risk level determines style:
  - MEDIUM: amber border, warning icon
  - HIGH: red border, pulsing glow, danger icon
- Shows: risk justification text, action count, action summary
- Two buttons:
  - "Approve" (green) → `sendMessage({type: "approve", action_id})`
  - "Reject" (red) → `sendMessage({type: "reject", action_id})`
- Reject dismisses the card + broadcasts cancellation

**Test**: Type a command in text input (voice comes later) → reasoning trace populates → Tavily results appear → action plan shows → approval gate appears for risky actions.

---

## Phase 4: Execution + Arm Control

### Backend

**Create `backend/agents/planner.py`:**
- `ActionPlanner` class
- `def plan_to_waypoints(action_plan: ActionPlan) -> list[list[float]]`:
  1. For each `ActionStep`:
     - `move_to` → look up target in `POSITION_MAP`, append waypoint
     - `grasp` → append current position with gripper value based on force
     - `release` → append current position with `GRIPPER_OPEN`
     - `pause` → no waypoint, just a delay marker
  2. Return list of 6-float waypoints
- Include safety check: all values within `JOINT_LIMITS`

**Create `backend/agents/executor.py`:**
- `ArmExecutor` class
- `__init__`: connect to SO101 via LeRobot
- `async def execute(waypoints: list, action_plan: ActionPlan)`:
  1. For each waypoint:
     a. Interpolate N intermediate steps from current to target
     b. Send each via `robot.send_action(torch.tensor(wp))`
     c. Broadcast `execution_update` with current step, positions, status
     d. Sleep `STEP_DELAY_S` between steps
  2. On completion: broadcast `execution_update` with `status="completed"`
  3. On error: broadcast error, attempt to return to home position
- `async def home()`: move to home position safely
- `def get_status()`: return current joint positions

**Wire into `main.py`:**
- After approval (or auto-approval for low risk):
  1. Planner converts ActionPlan → waypoints
  2. Executor runs waypoints
  3. Broadcast completion

### Frontend

**Create `components/panels/ArmStatus.jsx`:**
- Subscribe to `armStatus` from Zustand
- 6 horizontal progress bars (one per joint + gripper)
- Labels: J1 (Base), J2 (Shoulder), J3 (Elbow), J4 (Wrist Pitch), J5 (Wrist Roll), Grip
- Bar color:
  - Green: value within 50% of range
  - Yellow: value within 75% of range
  - Red: value > 90% of range (approaching limit)
- Gripper state icon: open hand / closed hand
- Numeric values displayed next to each bar
- Updates smoothly (CSS transition on width)

**Test**: Full pipeline end-to-end. Type command → perception → Tavily searches → plan → arm moves → dashboard shows everything.

---

## Phase 5: Voice Input + Dashboard Polish

### Frontend

**Create `hooks/useVoice.js`:**
```javascript
// Custom hook wrapping Web Speech API
// Returns: { isListening, transcript, interimTranscript, startListening, stopListening, isSupported }
// Uses webkitSpeechRecognition (Chrome) or SpeechRecognition
// interimResults: true for live transcription
// On final result: calls onResult(transcript) callback
// Error handling: falls back gracefully if not supported
```

**Create `components/voice/VoiceButton.jsx`:**
- Large circular button, bottom-center of dashboard
- States:
  - **Idle**: gray microphone icon, "Hold to speak" tooltip
  - **Listening**: pulsing red ring, waveform animation (CSS), live transcript below
  - **Processing**: spinning loader, "Thinking..." text
- Click/hold to activate (or toggle mode)
- Show `interimTranscript` in real-time below button
- On final transcript: send via WebSocket, add to command history
- Fallback: show text input field if speech not supported

**Create `components/voice/CommandHistory.jsx`:**
- Horizontal scrolling pills showing last 5 commands
- Click a past command to re-execute it
- Sits above the voice button

### Dashboard Polish Checklist

- [ ] Dark mode toggle works (shadcn built-in)
- [ ] All panels have proper loading states (skeleton shimmer)
- [ ] Error states show clearly (red alert banner with retry button)
- [ ] Smooth animations on panel updates (CSS transitions, not JS)
- [ ] Responsive: works on laptop (1280px+), doesn't need mobile
- [ ] Color-coded risk levels match SPECS.md tokens
- [ ] Tavily brand color (orange) used for search-related UI
- [ ] Nebius branding somewhere visible (footer or sidebar)
- [ ] Connection status dot: green=connected, yellow=reconnecting, red=disconnected
- [ ] Latency counters on perception and reasoning steps
- [ ] "Built with Nebius Token Factory + Tavily" footer badge

### Performance

- Camera frames: compress to quality=50 JPEG, max 2 FPS
- WebSocket: batch non-critical updates, send execution_update at 10Hz max
- Frontend: use `React.memo` on panels that don't change every frame
- Tavily cache: don't re-search identical queries

---

## Phase 6: Demo Prep + Submission

### Pre-Demo Checklist

```bash
# 1. Verify all APIs
python scripts/test_nebius.py
python scripts/test_tavily.py

# 2. Verify arm
python scripts/calibrate_arm.py  # if not already done

# 3. Start backend
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Start frontend
cd frontend && npm run dev

# 5. Open dashboard in Chrome (required for Web Speech API)
open http://localhost:5173

# 6. Test all 3 demo scenarios from SPECS.md
python scripts/demo_scenarios.py  # or run manually
```

### Demo Script (3 minutes for judges)

**Minute 1 — Hook + Live Demo 1 (Smart Pick)**
- "Every robot encounters objects it's never seen. ArmPilot solves this by searching the web before it acts."
- Tap mic: "Pick up the ceramic mug carefully"
- Point to dashboard: Tavily searching, reasoning trace, arm moving

**Minute 2 — Live Demo 3 (Safety) + Architecture**
- Place something risky (knife/glass)
- Tap mic: "Hand me that object"
- Point to: risk escalation → approval gate → cautious execution
- Brief architecture overview: "Nebius LLM brain, Tavily knowledge, LeRobot muscles"

**Minute 3 — Impact + Close**
- "This pattern generalizes to any robot handling novel objects. Open source. Built entirely today."
- Q&A ready

### Submission

1. Push code to public GitHub repo
2. Record 1-minute demo video (screen capture + camera angle of arm)
3. Upload video to YouTube (unlisted) or Loom
4. Submit at: https://cerebralvalley.ai/e/nebius-build-sf/hackathon/submit
5. Push dataset/model to HF org: `nebius-build-sf-2026-03`

---

## Common Failure Modes + Fixes

| Problem | Fix |
|---------|-----|
| VLM returns non-JSON | Retry with simpler prompt: "Return ONLY JSON, no markdown" |
| VLM returns wrong schema | Catch `ValidationError`, retry once, then use fallback scene |
| Tavily rate limited | Cache aggressively, reduce to 2 queries per command |
| Tavily timeout | 5s timeout, return fallback string, proceed without web knowledge |
| Arm doesn't respond | Check USB port, re-calibrate, restart LeRobot connection |
| Arm hits joint limits | `JOINT_LIMITS` check in planner, clamp values, never send raw LLM output |
| WebSocket disconnects | Auto-reconnect in frontend with exponential backoff (1s, 2s, 4s, max 10s) |
| Camera not found | Fallback to static scene description, still demo reasoning + Tavily |
| No speech support | Text input fallback, always available |
| LLM hallucinates actions | Validate against allowed action types, reject unknowns |
| Demo object not detected | Pre-place objects in known positions, have backup hardcoded scene |

---

## Code Style Rules

- **Python**: type hints everywhere, async/await for all I/O, Pydantic for all data models
- **React**: functional components only, hooks for all state, Zustand for global state
- **No classes in React** — only function components
- **shadcn/ui** for all base UI components — never write custom buttons/cards/badges from scratch
- **Tailwind only** — no custom CSS files (except globals.css for shadcn vars)
- **No console.log in production** — use a proper logger or remove
- **All WebSocket events validated** against Pydantic models before broadcast
- **Error boundaries** around each panel so one crash doesn't kill the dashboard

---

## Key Integration Points

### Nebius Token Factory → OpenAI SDK
```python
from openai import OpenAI
client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1",
    api_key=os.getenv("NEBIUS_API_KEY")
)
# Use exactly like OpenAI: client.chat.completions.create(...)
```

### Tavily → Python SDK
```python
from tavily import TavilyClient
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
results = client.search("query", search_depth="basic", max_results=3)
# results["results"] = [{title, content, url, score}, ...]
```

### OpenRouter → OpenAI SDK (for vision)
```python
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
# Vision: pass image as base64 in message content array
```

### LeRobot → SO101
```python
from lerobot.common.robot_devices.robots.factory import make_robot
robot = make_robot("so101_follower", port="/dev/ttyACM0", id="armpilot")
robot.send_action(torch.tensor([j1, j2, j3, j4, j5, gripper]))
```

### Web Speech API → WebSocket
```javascript
const recognition = new webkitSpeechRecognition();
recognition.continuous = false;
recognition.interimResults = true;
recognition.lang = 'en-US';
recognition.onresult = (e) => {
    if (e.results[0].isFinal) {
        ws.send(JSON.stringify({ type: 'command', text: e.results[0][0].transcript }));
    }
};
```
