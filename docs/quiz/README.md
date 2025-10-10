# Quiz API

## What It Does
Provides a longer-form questionnaire to deepen partner insight and stores quiz submissions. Requests map through `api-container/app/controllers/quiz_controller.py`; persistence and scoring live in `api-container/app/services/quiz_service.py`.

## Endpoints & Critical Attributes
- `GET /api/quiz/status` *(JWT required)*  
  **Response:**  
  - `has_taken_quiz`: boolean.  
  - `quiz_count`: total submissions.  
  - `latest_quiz_date`: ISO timestamp of newest attempt.  
  - `available_questions`: count of current question bank.
- `GET /api/quiz/questions` *(JWT)*  
  **Response:** array of question objects (`id`, `question`, `type`, optional `options`) and `total_questions`.
- `POST /api/quiz/submit` *(JWT)*  
  **Body:** `answers` list.  
  **Response:** `quiz_id`, simple `score` (length of answers), `total_questions`, success message.

## Core Logic Flow
1. **Question bank** — statically defined list enables deterministic frontend rendering.
2. **Submission validation** — ensures `answers` is a list before inserting into `quiz_responses`.
3. **Persistence fields:** `user_id`, `answers`, `created_at`, derived `score`. Additional helper `get_user_quiz_results` expands stored records with ISO timestamps.
4. **Status checks** — counts documents and inspects the latest submission to build dashboard-friendly status info.

## Interaction With Other APIs
- Requires Auth-issued JWT to identify the submitting user.
- Quiz insights can be surfaced alongside Daily Questions for reflective discussions; Messages can notify partners about quiz completion.
- Partner linkage is not required, but `quiz_responses` can be filtered by both partner IDs to compare results in analytics features.

## Why Offer This Quiz
Acts as a structured conversation starter and baseline assessment beyond daily prompts. The stored history enables progress tracking or personalized recommendations later.

## If You’re Stuck
- Follow handler implementations in `quiz_controller.py` for request/response shapes.
- Inspect `QuizService.submit_quiz_answers` to understand validation and document layout.
- Review MongoDB insert patterns (`mongo.db.quiz_responses.insert_one`) if new to PyMongo.
- Learn more about designing survey schemas from [MongoDB schema design docs](https://www.mongodb.com/docs/manual/core/data-model-design/).
