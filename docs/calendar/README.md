# Calendar API

## What It Does
Stores and surfaces shared events for partners, ensuring both users see upcoming plans. Routes are implemented in `api-container/app/controllers/calendar_controller.py`; core logic is in `api-container/app/services/calendar_service.py`.

## Endpoints & Critical Attributes
- `GET /api/calendar/events` *(JWT required)*  
  **Query params:** optional `year`, `month` (ints).  
  **Response:** `{ "events": [...] }` where each event bundles `_id`, `title`, `description`, `date`, `time`, `creator_id`, `creator_name`. Pulls both the user’s and their connected partner’s records.
- `POST /api/calendar/events` *(JWT)*  
  **Body:** `title`, `date` (`YYYY-MM-DD`), `time` (`HH:MM`), optional `description`.  
  **Response:** confirmation message plus the saved event echoing core fields.

## Core Logic Flow
1. **User lookup** — `_get_user` fetches the calling user, stringifying `_id`. Missing users short-circuit with errors.
2. **Partner inclusion** — when `partner_status == "connected"` the partner’s `user_id` is appended so queries fetch shared events.
3. **Date filtering** — builds a `match_stage` to filter by user IDs and, when `year/month` supplied, constructs start/end-of-month bounds that support both legacy `start_time` datetimes and newer `date` strings.
4. **Event formatting** — ensures each event has human-friendly `date`/`time`, inferring them from `start_time` if necessary, and resolves `creator_name` via cached user lookups.
5. **Creation** — validates required fields, parses combined `date` + `time` into a `start_time` datetime, and stores metadata (`creator_id`, `creator_name`, `created_at`).

## Interaction With Other APIs
- Depends on Auth for identifying users and retrieving partner relationships.
- Complements Messages scheduling: both rely on consistent ISO strings and UTC conversion, making it straightforward for workers or frontends to cross-reference reminders.
- Partner invitations accepted via Auth populate the `partner_id` used for shared visibility.
- Calendar entries can be informed by Daily Question answers (e.g., plan activities) or celebrate milestones after quiz insights.

## Why Manage Events Here
Keeps plans contextually close to conversations and prompts, encouraging consistent engagement within the product instead of switching to external calendars. Shared visibility reinforces partner alignment.

## If You’re Stuck
- Inspect `calendar_controller.py` for request parsing and response shapes.
- Walk through `CalendarService.get_events_for_month` to understand Mongo query composition.
- Review Python [`datetime` docs](https://docs.python.org/3/library/datetime.html) for month boundary calculations.
- Check inserted document structure in `CalendarService.create_event` before writing migrations or analytics.
