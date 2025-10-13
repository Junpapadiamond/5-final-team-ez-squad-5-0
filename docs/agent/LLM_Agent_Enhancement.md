# Agent LLM Enhancement Blueprint

## High-Level Goals
- Move the Together Agent away from heuristic-only logic toward OpenAI-powered, context-aware insights.
- Keep the API surface compatible with existing clients while layering richer tone analysis and coaching guidance.
- Provide fallbacks and cost controls so the experience remains responsive even if the LLM is unavailable.

## Where to Integrate LLMs
1. **AgentAnalysisService** (`api-container/app/services/agent_analysis_service.py`)
   - Replace regex/word-count checks with an LLM call that returns a structured JSON payload (sentiment, confidence, emotional drivers, coaching tips, suggested reply).
   - Service orchestrates context gathering, schema validation, and fallback to the legacy heuristic when the model call fails or JSON parsing breaks.
2. **AgentSuggestionService** (`api-container/app/services/agent_suggestion_service.py`)
   - Feed recent conversations, daily questions, and upcoming events through an LLM that returns “next best action” cards (title, summary, confidence, call-to-action).
   - Blend LLM cards with deterministic reminders (e.g., unanswered daily question) when needed.
3. **StyleProfileService** (`api-container/app/services/style_profile_service.py`) *(optional)*
   - Ask the LLM to summarize message history (tone, pacing, emoji usage, sample phrases) instead of purely relying on token frequencies.

## Proposed Workflow
1. **Context Assembly**
   - Collect recent messages (both partners), daily-question answers, upcoming events, partner status, and cached style profile snippets.
   - Sanitize PII and trim to fit the target model’s token limits. Label each section clearly (e.g., “Messages: …”, “Daily Prompt: …”).
2. **Agent Orchestrator**
   - Introduce a dedicated `AgentOrchestrator` service that decides which LLM routines to run.
   - Prompts to support:
     - *Tone Analyzer* — evaluate a draft message, return sentiment, empathy score, red flags, and suggested reply moves.
     - *Coaching Planner* — generate action cards (message drafts, reminders, calendar ideas).
     - *Style Profiler* *(optional)* — highlight communication patterns and strengths.
3. **Schema & Validation**
   - Use OpenAI JSON mode (or Pydantic validation) for consistent structured output.
   - Map results back to existing REST responses so the frontend continues to function even as data richness increases.
4. **Fallback Layer**
   - Keep the existing deterministic logic as a fallback when the LLM call fails or the API key is missing.
   - Return an explicit flag (e.g., `ai_source: "legacy" | "openai"`) so clients can display “offline mode” messaging.
5. **Caching & Cost Control**
   - Cache tone analyses per message hash and coaching suggestions per user/day to reduce duplicate calls.
   - Default to lighter models (`gpt-4o-mini`, `o1-preview`) and only escalate to premium models when explicitly requested.
6. **Frontend Communication**
   - Continue surfacing UI badges that indicate which sections are LLM powered vs. logic fallback.
   - Provide tooltips or banners when AI guidance is unavailable.

## Implementation Phases
1. Build an `AgentLLMClient` that wraps the OpenAI Responses API with helpers such as `analyze_tone()`, `plan_coaching()`, `summarize_style()`. Each helper should accept structured context objects and return validated dataclasses.
2. Refactor `AgentAnalysisService.analyze_input` to use `AgentLLMClient.analyze_tone()`, merge the LLM insights with style profile data, and fall back gracefully on errors.
3. Extend `AgentSuggestionService.get_suggestions` to call `AgentLLMClient.plan_coaching()` and merge with legacy reminders where appropriate.
4. Update automated tests:
   - Unit tests using mocked LLM responses to cover orchestration and schema validation.
   - Integration test(s) verifying the fallback path when `OPENAI_API_KEY` is absent.
5. Introduce feature toggles/configuration flags (`AGENT_LLM_ENABLED`, `AGENT_MODEL_TONE`, `AGENT_MODEL_COACHING`) to roll out incrementally and gather performance data.

## Next Steps
- Implement the orchestrator and LLM client scaffolding.
- Update backend endpoints to return the richer payloads while preserving compatibility.
- Refresh frontend components so AI-driven sections are clearly distinguished and actionable.
