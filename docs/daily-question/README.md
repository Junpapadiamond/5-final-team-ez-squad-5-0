# Daily Question API

## What It Does
Surfaces a reflective prompt per user each day and records their answer. HTTP handlers reside in `api-container/app/controllers/daily_question_controller.py`; persistence logic is in `api-container/app/services/daily_question_service.py`.

## Endpoints & Critical Attributes
- `GET /api/daily-question/` *(JWT required)*  
  **Response fields:**  
  - `question`: deterministic string pulled from `DAILY_QUESTIONS`.  
  - `date`: ISO date string for the question slot.  
  - `answered`: boolean flag.  
  - `answer`: latest answer if already submitted.
- `POST /api/daily-question/answer` *(JWT)*  
  **Body:** `answer` (string).  
  **Response:** echo of `question`, stored `answer`, and `date`.
- `GET /api/daily-question/answers` *(JWT)*  
  Placeholder returning `user_answer`, `partner_answer`, `both_answered`.

## Core Logic Flow
1. Seeds the RNG with `date.today().isoformat() + user_id` so each user gets a repeatable prompt for the day.
2. Stores questions and answers in the `daily_questions` collection with fields: `user_id`, `question`, `date`, `answer`, `answered`, timestamps.
3. Update operations use `$set` to mark `answered=True`, attach the answer, and record `answered_at`.

## Collaboration With Other APIs
- Relies on Auth to supply `user_id` via JWT.
- Partner answers are planned for cross-linking once partner retrieval logic is completed; until then, Messages or Calendar can be used to discuss answers externally.
- Daily reflections complement the longer-form Quiz entries (`quiz_responses`) and can be surfaced in the frontend alongside Messages for daily check-ins.

## Why Capture Daily Prompts
Encourages lightweight, consistent engagement that builds relationship context. The deterministic selection avoids duplicates during a day while keeping implementation simple.

## If You’re Stuck
- Step through `DailyQuestionService.get_today_question` to see seeding and persistence.
- Review Mongo write patterns in the same service to understand updates.
- Brush up on Python’s [`random` seeding](https://docs.python.org/3/library/random.html#random.seed) to grasp why questions repeat per day.
- Check controller decorators in `daily_question_controller.py` for authentication requirements.
