# CLAUDE.md

This is the ArmPilot hackathon project for Nebius Build SF (March 15, 2026).

## Role

This Claude instance is working as **Person A**. Refer to [PLAN_PERSON_A.md](./PLAN_PERSON_A.md) for task assignments.

## Required Reading

Before doing any work, read these files in order:

1. **[SPECS.md](./SPECS.md)** — Complete technical specification: architecture, API contracts, WebSocket protocol, Pydantic models, component specs, demo scenarios.
2. **[SKILLS.md](./SKILLS.md)** — Build instructions: phase-by-phase implementation guide, integration points, failure modes, environment setup.
3. **[PROJECT_PLAN.md](./PROJECT_PLAN.md)** — Strategic plan: team roles, dashboard sources, sponsor integration, component sources.

Also available:
- **[PLAN_PERSON_A.md](./PLAN_PERSON_A.md)** — Person A task breakdown
- **[ARCHITECTURE.mermaid](./ARCHITECTURE.mermaid)** — Visual architecture diagram

## Quick Summary

ArmPilot is a voice-controlled SO101 robotic arm powered by an LLM agentic pipeline. The user speaks a command → reasoning agent uses Tavily web search → plans physical actions → executes on the SO101 arm → streams every decision to a live Mission Control dashboard.

**Stack**: FastAPI (backend) + React/Vite/shadcn (frontend) + Nebius Token Factory LLMs + Tavily search + LeRobot SO101 arm control

## Development Approach: Test-Driven Development (TDD)

実装は必ずテスト駆動で行う。

1. **Red** — 失敗するテストを先に書く
2. **Green** — テストが通る最小限の実装を書く
3. **Refactor** — テストを通したまま整理する

- Python: `pytest` を使用。テストは `tests/` に置く
- TypeScript/React: `vitest` を使用。テストは `*.test.ts` / `*.test.tsx`
- 新機能・バグ修正どちらもテストを先に書いてから実装する
- テストなしのコードはマージしない

## Git Workflow

- Commit and push directly to `main` — no branches, no PRs.
