# Together Platform APIs

## System Snapshot
- **Auth** issues JWT access tokens, owns user lifecycle, and brokers partner invitations.
- **Daily Question** rotates reflective prompts per user and records answers for the day.
- **Quiz** delivers the longer-form compatibility questionnaire and stores submissions.
- **Messages** supports instant and scheduled partner messaging with optional email alerts.
- **Calendar** keeps couples on a shared timeline by storing personal and partner events.

Every request beyond registration/login flows through Auth for identity, then fans out to service-specific MongoDB collections. Partner status lives on the user documents and is the connective tissue for the other features.

## Shared Infrastructure
- **MongoDB collections**  
  `users`, `partner_invitations`, `quiz_responses`, `daily_questions`, `messages`, `scheduled_messages`, `events`.
- **Security boundary**  
  JWT signature keys in `app/config.py` guard all authenticated routes. Controllers call `get_jwt_identity()` to look up the current user before touching data.
- **Notifications**  
  `app/email_utils.py` pipes key actions—invites, partner messages—through email. Services swallow email failures so primary flows succeed.

## Typical User Journey
1. **Sign up (`/api/auth/register`)** — user is persisted, token issued, optional partner invite kicked off.
2. **Partner link** — invite acceptance flips both users’ `partner_status` to `connected`; Messages and Calendar now auto-target the partner.
3. **Engage daily**  
   - Pull today’s prompt (`/api/daily-question/`) and answer it.  
   - Swap quick notes (`/api/messages/send`) or schedule encouragement (`/api/messages/schedule`).  
   - Drop milestones on the shared calendar (`/api/calendar/events`).
4. **Deepen connection** — run the quiz (`/api/quiz/questions` + `/submit`) for longer-form reflections; view status later.

Keeping this order in mind clarifies cross-service dependencies: without Auth there is no identity; without partner linkage most collaborative actions gracefully decline.

## Where to Dig Deeper
- Start with `api-container/app/__init__.py` to see blueprint registration and middleware wiring.
- Each controller under `api-container/app/controllers/` maps HTTP routes; the paired service module carries the database logic.
- Cross-service data model lives on the `users` collection (partner IDs, notification flags).

## Learning Resources
- [Flask documentation](https://flask.palletsprojects.com/) for request handling and Blueprints.
- [Flask-JWT-Extended docs](https://flask-jwt-extended.readthedocs.io/) for token flows.
- [MongoDB basics](https://www.mongodb.com/docs/manual/core/document/) to understand document updates and queries.
- [Project README](../../README.md) for environment and runtime setup.
