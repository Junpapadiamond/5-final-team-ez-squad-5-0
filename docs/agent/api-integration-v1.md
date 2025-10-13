# API Integration v1 – LLM-Powered Agent

## Overview
Documenting the changes that brought OpenAI-powered insights into the Together API and stabilized the frontend experience.

## Key Deliverables
- `AgentLLMClient` wraps OpenAI Responses/Chat APIs with schema validation and fallback logic.
- `AgentOrchestrator` assembles context (messages, events, daily questions) for each analysis run.
- `AgentAnalysisService` and `AgentSuggestionService` now rely on the orchestrator, cache results, and fall back to deterministic heuristics when needed.
- Normalization pipelines convert all LLM payloads to primitive strings/numbers before returning to the frontend, preventing React render errors.
- `StyleProfileService` can incorporate LLM summaries while keeping deterministic metrics.

## Configuration Flags
| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | – | Required for any OpenAI interaction. |
| `AGENT_LLM_ENABLED` | `"1"` | Master toggle for LLM calls. |
| `AGENT_MODEL_TONE` | `gpt-4o-mini` | Tone analysis model. |
| `AGENT_MODEL_COACHING` | `gpt-4o-mini` | Coaching suggestions model. |
| `AGENT_MODEL_STYLE` | `gpt-4o-mini` | Style summary model. |
| `AGENT_TONE_CACHE_HOURS` | `3` | Cache TTL for tone analysis results. |
| `AGENT_COACHING_CACHE_HOURS` | `6` | Cache TTL for coaching cards. |

## Core Code Changes
- `api-container/app/services/agent_llm_client.py` — new helper with JSON-mode prompts, fallback to chat completions, payload normalization.
- `api-container/app/services/agent_orchestrator.py` — gathers Mongo context and calls the LLM client.
- `api-container/app/services/agent_analysis_service.py` — uses orchestrator output, writes to Mongo caches, emits `ai_source`.
- `api-container/app/services/agent_suggestion_service.py` — blends LLM cards with legacy reminders and caches results.
- `api-container/app/services/style_profile_service.py` — accepts LLM summaries, normalizes stored documents.
- `frontend/src/app/agent/page.tsx` — highlights AI vs logic sections, renders suggested replies and warnings.
- `frontend/src/lib/api.ts` — exposes `analyzeAgentMessage`.
- Tests updated in `api-container/tests` to cover LLM success/fallback scenarios.

## Deployment Checklist
1. `docker compose build api && docker compose up -d api`
2. Validate `pip show openai` inside container (≥1.35) and confirm `OPENAI_API_KEY` env is present.
3. Hit `/api/agent/analyze` with a sample draft → confirm `ai_source: "openai"` and populated `llm_feedback`.
4. Refresh frontend Agent page → tone analyzer should render analytics plus OpenAI feedback without errors.

---

## Performance & Token Reduction Ideas (Future Work)
1. **Trim Context** — cap recent messages/events to the last 3 items, drop redundant fields, reuse cached style summaries instead of recomputing every call.
2. **Prompt Optimization** — tighten max tokens, request concise bullet lists, reuse prompt templates per session.
3. **Async Updates** — load tone analysis immediately but defer coaching suggestions to a background fetch for perceived speed.
4. **Usage Monitoring** — log token usage from OpenAI responses and introduce throttling or feature flags for high-volume users.
