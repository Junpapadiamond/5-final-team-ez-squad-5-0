# Messages API

## What It Does
Handles direct messaging between partners, including immediate sends, scheduled deliveries, inbox queries, and conversation views. HTTP layer: `api-container/app/controllers/messages_controller.py`; business logic: `api-container/app/services/messages_service.py`.

## Endpoints & Critical Attributes
- `GET /api/messages/messages` *(JWT required)*  
  Returns up to 100 recent messages where the user is sender or receiver. Each item includes `_id`, `sender_id`, `sender_name`, `recipient_id`, `recipient_name`, `content`, `timestamp`, `is_scheduled`, `is_read`.
- `POST /api/messages/send` *(JWT)*  
  **Body:** `content`, optional `receiver_id`.  
  Auto-resolves partner via `partner_id` when omitted. Sends email notification if the recipient enabled alerts.
- `POST /api/messages/schedule` *(JWT)*  
  **Body:** `content`, `scheduled_for` (ISO string, accepts `Z` suffix), optional `receiver_id`.  
  Persists to `scheduled_messages` with `status="pending"`.
- `GET /api/messages/scheduled` *(JWT)*  
  Lists scheduled messages with `_id`, `content`, `scheduled_for`, `sender_name`, `status`.
- `PUT /api/messages/scheduled/<message_id>` *(JWT)*  
  **Body:** optional `content`, optional `scheduled_for`. Updates pending scheduled messages in place.
- `POST /api/messages/scheduled/<message_id>/cancel` *(JWT)*  
  Cancels a pending scheduled message if owned by the caller and still pending. Returns an explanatory error if it can’t be cancelled.
- `GET /api/messages/conversation/<partner_id>` *(JWT)*  
  Pulls chronological conversation history, marks partner-sent messages as read.

## Core Logic Flow
1. **User resolution** — `_get_user` fetches user docs, caching results per request to avoid redundant queries.
2. **Partner defaulting** — `_resolve_partner_id` checks `partner_status == "connected"` before assuming a receiver; otherwise requires explicit `receiver_id`.
3. **Message formatting** — `_format_message` normalizes Mongo docs into API-ready dictionaries, stringifying IDs and timestamps.
4. **Scheduling** — normalises any ISO 8601 input (with offsets or `Z`) to UTC before persisting so the worker (not shown here) has a consistent reference point. Endpoints expose `scheduled_for` in UTC (`...Z`).
5. **Edits & cancellations** — `update_scheduled_message` lets users tweak pending messages without recreating them; cancellation surfaces clear reasons when a message is already processed.
6. **Notifications** — `send_partner_message` emails recipients when `email_notifications` is true, but exceptions are swallowed to prioritise messaging success.

## Interaction With Other APIs
- Auth supplies JWT identity and exposes partner linkage fields that drive receiver resolution.
- Partner invitations accepted through the Auth API populate the `partner_id` required for default messaging targets.
- Calendar events and scheduled messages can coordinate reminders; both rely on consistent datetime formatting.
- Daily Question answers or Quiz results can be shared through Messages to spark conversation.

## Why Provide Messaging
Creates an immediate feedback loop that keeps couples engaged inside the platform. Scheduled messaging supports intentionality (anniversary reminders, encouragement) without needing a separate tool.

## If You’re Stuck
- Read controller methods in `messages_controller.py` to see request validation patterns.
- Step through `MessagesService.send_message` and `schedule_message` for receiver resolution logic.
- Review [Python datetime timezone handling](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects) to understand the UTC normalization.
- Check Mongo query examples in the service for filtering and sorting records.
