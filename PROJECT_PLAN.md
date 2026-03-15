# ArmPilot — Updated Project Plan (v2)

## Quick Links
- **SPECS.md** — Complete technical specification (architecture, API contracts, schemas, component specs)
- **SKILLS.md** — Claude Code build skill (phase-by-phase instructions, integration points, failure modes)
- **This file** — Strategic plan, team roles, dashboard sources, sponsor integration

---

## Dashboard Implementation Strategy

### Base Template: Fork `satnaing/shadcn-admin`
- **Why**: Most starred shadcn dashboard on GitHub. Vite + React + Tailwind + shadcn/ui.
- **What to keep**: Sidebar layout, dark/light toggle, Cmd+K command menu, responsive grid.
- **What to strip**: All demo pages (users, settings, tasks, chats, apps).
- **What to add**: 6 custom panels (Camera, Scene, Reasoning, Tavily, Arm, Approval).

### Component Sources (steal patterns from):

| Dashboard Panel | Source Repo | What to Grab |
|----------------|-------------|--------------|
| Reasoning Trace (timeline) | `evilmartians/agent-prism` | `TraceViewer` component, span tree layout, timing bars |
| Camera Streaming | `ddelago/Real-Time-Robotics-Dashboard` | Base64 frame → WebSocket → `<img>` pattern |
| Arm Telemetry | `Relativiteit/ros-robot-control-dashboard` | Joint position bars, robot state display |
| LLM Observability | `prajeesh-chavan/OpenLLM-Monitor` | WebSocket real-time update pattern, Zustand store shape, alert system |
| Robot Fleet UI | `transitiverobotics/transact` | Video panel layout, ShadCn component patterns |

### Dashboard Build Order (for Person 3 — Frontend Dev):

**Hour 0-1**: Fork shadcn-admin, strip demos, set up WebSocket hook + Zustand store, create empty 6-panel grid layout.

**Hour 1-2**: `CameraFeed.jsx` (base64 img tag) + `SceneViewer.jsx` (object cards from perception JSON).

**Hour 2-3**: `ReasoningTrace.jsx` (vertical timeline, adapt agent-prism patterns) + `TavilyResults.jsx` (scrolling search cards with orange accent).

**Hour 3-4**: `ArmStatus.jsx` (6 joint bars + gripper) + `ApprovalGate.jsx` (risk-colored approval modal).

**Hour 4-5**: `VoiceButton.jsx` (mic button + Web Speech API) + `CommandHistory.jsx` (recent commands). Polish: animations, loading states, error banners.

**Hour 5-6**: Help record demo video, test all 3 scenarios.

---

## Team Roles (4 people)

| Role | Person | Focus | Deliverables |
|------|--------|-------|-------------|
| **Lead / Reasoning Agent** | You (Kush) | `reasoning.py`, `tavily_search.py`, Nebius LLM integration, agent loop orchestration in `main.py` | Working reasoning pipeline: command → Tavily → plan |
| **Hardware / Arm** | Teammate 2 | SO101 calibration, LeRobot setup, `executor.py`, `planner.py`, calibrate `POSITION_MAP` | Arm moves to waypoints on command |
| **Frontend / Dashboard** | Teammate 3 | Fork shadcn-admin, all 6 panels, `useWebSocket.js`, `useVoice.js`, Zustand store | Live dashboard showing full pipeline |
| **Infra / Perception** | Teammate 4 | `main.py` FastAPI + WS hub, `perception.py`, `vision.py`, camera setup, VLM integration | Camera → VLM → scene JSON flowing |

### Parallel Tracks (First 2 Hours)

```
Track A (Hardware):  Calibrate SO101 → Test basic moves → Record POSITION_MAP values
Track B (Backend):   FastAPI skeleton → Test Nebius API → Test Tavily API → Wire perception
Track C (Frontend):  Fork shadcn-admin → Strip → Layout grid → WebSocket hook → Camera panel
Track D (Reasoning): Write prompts → Test Tavily queries → Build reasoning agent → Test end-to-end
```

All tracks converge at Hour 2 for integration.

---

## Sponsor Integration Summary

| Sponsor | Component | Integration Depth | Demo Visibility |
|---------|-----------|-------------------|-----------------|
| **Tavily** | `tavily_search.py` — every action grounded in web search | DEEP — core to reasoning pipeline | HIGH — search queries + results visible on dashboard |
| **Nebius Token Factory** | `reasoning.py` + `vision.py` — LLM brain | DEEP — powers all inference | HIGH — model name shown in trace |
| **OpenRouter** | `vision.py` fallback — vision model | MEDIUM — fallback for VLM | LOW — transparent to user |
| **Hugging Face** | LeRobot library + HF org for sharing | MEDIUM — arm control layer | MEDIUM — mention in pitch |
| **Oumi** | Stretch: fine-tune on action data | LOW — only if time | LOW — mention as "next step" |
| **Toloka** | Stretch: run security eval preset | LOW — post-build validation | LOW — mention in pitch |
| **Cline** | Development tool | META — use during hacking | NONE — invisible to judges |

---

## Critical Path Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SO101 calibration fails | MEDIUM | CRITICAL | Start calibration FIRST. Have backup: hardcoded positions from LeRobot docs |
| No vision model on Nebius TF | HIGH | MEDIUM | OpenRouter has `qwen/qwen2.5-vl-72b-instruct` as backup |
| Tavily rate limit | LOW | MEDIUM | Cache results, limit 3 queries per command, pre-search common objects |
| Arm can't reach demo positions | MEDIUM | HIGH | Pre-map only 5 positions within confirmed reach. Test each position during calibration |
| LLM output not parseable | MEDIUM | MEDIUM | Retry with simplified prompt, catch errors, validate with Pydantic |
| WebSocket drops under load | LOW | LOW | Auto-reconnect in frontend, batch non-critical updates |
| Camera not detected | LOW | HIGH | Test camera at start. Fallback: hardcoded scene for demo |
| Chrome blocks mic access | LOW | MEDIUM | Use HTTPS or localhost (both work). Text input always available |

---

## Files to Give Claude Code

When starting Claude Code, provide these files in order:

1. **SPECS.md** — Complete technical specification
2. **SKILLS.md** — Build instructions and integration guide  
3. **This plan** (optional) — Strategic context

Then tell Claude Code:

> "Read SPECS.md and SKILLS.md. Build ArmPilot Phase 1 first — FastAPI backend with WebSocket, React frontend with shadcn-admin layout, and Zustand store. Follow the exact directory structure and WebSocket protocol in SPECS.md."

For subsequent phases:

> "Move to Phase 2. Build the perception pipeline — perception.py, vision.py, CameraFeed.jsx, and SceneViewer.jsx. Follow SKILLS.md Phase 2 instructions."

---

## Submission Checklist

- [ ] Public GitHub repo with all code
- [ ] README.md with project description, setup instructions, architecture diagram
- [ ] 1-minute demo video uploaded to YouTube/Loom
- [ ] Submitted via https://cerebralvalley.ai/e/nebius-build-sf/hackathon/submit
- [ ] Model/dataset pushed to HF org `nebius-build-sf-2026-03`
- [ ] All sponsor tools credited in README
- [ ] Code runs from clean clone (no hardcoded local paths)
