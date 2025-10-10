# Quiz API

## What It Does
Runs partner-synchronised compatibility sessions where both users answer the same “this or that” prompts and receive a live alignment score. HTTP layer: `api-container/app/controllers/quiz_controller.py`; orchestration and scoring: `api-container/app/services/quiz_service.py`.

## Endpoints & Critical Attributes
- `GET /api/quiz/status` *(JWT required)*  
  Returns aggregated metrics: `total_sessions`, `completed_sessions`, `active_session_id`, `last_score`, `average_score`, and the size of the question bank.
- `GET /api/quiz/questions` *(JWT)*  
  Exposes the curated compatibility prompt bank (`id`, `question`, `options`, `category`) plus `default_batch_sizes`.
- `POST /api/quiz/session/start` *(JWT)*  
  **Body:** optional `question_count` or explicit `question_ids`.  
  Creates (or returns) the active session for the connected partners. Response includes `created` flag alongside the session payload.
- `GET /api/quiz/session/current` *(JWT)*  
  Retrieves the latest in-progress session, or `session: null` when none exists.
- `GET /api/quiz/session/<session_id>` *(JWT)*  
  Fetches a specific session (in progress or completed) if the caller is a participant.
- `POST /api/quiz/session/<session_id>/answer` *(JWT)*  
  **Body:** `question_id`, `answer`.  
  Records the caller’s answer, recomputes compatibility if both partners have finished, and returns the refreshed session state.

Every session document includes:
- `questions`: sampled list with per-question `your_answer`, `partner_answer`, and `is_match`.
- `progress`: counts of completed answers and which questions are awaiting the partner.
- `compatibility`: final summary (`matches`, `total`, `score`, `completed_at`) once finished.

## Core Logic Flow
1. **Partner validation** — starting a session requires `partner_status == "connected"`. The service reuses existing in-progress sessions to keep both users aligned.
2. **Question sampling** — selects a random subset from `COMPATIBILITY_QUESTIONS`, unless callers specify exact IDs.
3. **Answer tracking** — nested `responses` map (`responses[user_id][question_id]`) keeps both sides’ answers. Each submission rewrites the response map atomically.
4. **Completion & scoring** — when every question has both answers, the service marks the session `completed`, stores a `compatibility_summary`, and reports a percentage match.
5. **Status insight** — historic sessions live in the `quiz_sessions` collection, enabling averages, last score time stamps, and active session lookups without reprocessing.

## Interaction With Other APIs
- Auth: provides user identity and partner linkage; without a connected partner, session creation fails with a helpful message.
- Messages: can surface compatibility outcomes (e.g., send a congratulatory note) by pulling from the session summary.
- Daily Questions: complements the quick-alignment quiz with deeper reflective prompts; both share the `users` partner metadata.

## Why Offer Partner Sessions
Instant, gamified insight encourages couples to talk through differences while celebrating overlaps. Allowing custom lengths (10/15/20 or custom counts) keeps replays fresh and tailored.

## If You’re Stuck
- Review `QuizService.start_session` for sampling logic and partner checks.
- Examine `QuizService.submit_session_answer` to see how completions and scores are computed.
- Use `GET /api/quiz/session/<id>` to debug stored payloads directly.
- The curated prompt list lives at the top of `quiz_service.py`; adjust or extend there when adding new themes.
