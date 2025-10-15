# Updates – October 14

## Backend
- **Immediate activity capture** – Messages, daily answers, calendar creation, and quiz completion route through `AgentActivityService.record_event(...)` as soon as the Mongo write succeeds (`messages_service.py`, `daily_question_service.py`, `calendar_service.py`, `quiz_service.py`). Each call attaches scenario tags (`daily_check_in`, `anniversary_planning`, `quiz_follow_up`) and per-event metadata (message preview, quiz score, calendar window) so downstream workflows have richer context without requerying.
- **Always-on ingestion** – Added an `agent-worker` entry in `docker-compose.yml` that runs `workers/agent_activity_worker.py` under the same image as the message worker. This ensures change polling (messages, quiz sessions, calendar gaps) continues outside the dev shell and removes the need for a manual `python workers/...` invocation.
- **LLM-first planning** – `AgentLLMClient` now exposes an action-plan schema in JSON mode, returning actions, strategy, explanation, and model identifiers. `AgentWorkflowEngine.evaluate_event` feeds the triggering event + assembled context into the new `plan_actions` call; responses populate `AgentActionPlan.llm_metadata` (model, strategy, raw payload hash) and only fall back to legacy deterministic handlers if the LLM returns no actionable cards.
- **Suggestion package redesign** – `AgentSuggestionService` no longer merges heuristics. It expects the orchestrator to supply `{cards, strategy, explanation}` and stores that bundle (including model name and timestamp) in `agent_coaching_cache`. Cache keys stay per-user, but the payload now mirrors the API response, which simplifies consumer code.
- **Controller integration** – `/api/agent/actions` emits `llm` metadata alongside suggestion arrays, and `/api/agent/queue` runs `AgentDecisionService.process_pending_events` before reading Mongo so the UI sees any freshly enqueued LLM plans. Activity endpoints remain unchanged apart from the richer stored documents.

## Frontend
- **LLM visibility** – Agent Ops (`agent/page.tsx`) consumes the `llm` block and per-card metadata to render badges (model name), strategy text, and reasoning snippets. Queue items now show the same model badges and call-to-action text derived from the LLM payload. The tone analyzer header displays the active model and emits an amber warning whenever it fell back to heuristics, so users can distinguish AI vs legacy analysis.
- **Monitor payloads** – Dashboard components (`dashboard/page.tsx`) append message previews, question titles, or event snippets underneath each captured activity. Queue tiles highlight LLM model badges and pending/complete states so the pipeline cards (capture → plan → execute → feedback) explain what the agent is doing with concrete data.

## Quality
- Updated API client typings (`AgentQueueAction`, `getAgentSuggestions`) to surface `llm_metadata`, confidence, and strategy fields end-to-end.
- Added focused tests (`tests/test_agent_suggestions.py`) stubbing the orchestrator to supply LLM data and verifying the controller decorates responses with metadata while the queue route remains callable with patched dependencies.
- Verified the slice via `./venv/bin/python -m pytest api-container/tests/test_agent_suggestions.py`.
