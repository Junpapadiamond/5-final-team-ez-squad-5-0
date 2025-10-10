# Auth API

## What It Does
Manages user onboarding, authentication, profile maintenance, and partner invitations. Controllers live in `api-container/app/controllers/auth_controller.py`; business rules sit in `api-container/app/services/auth_service.py` and `partner_service.py`.

## Endpoints & Critical Attributes
- `POST /api/auth/register`  
  **Body:** `name`, `email`, `password`, optional `partner_email`.  
  **Response:** `user` document (sans `password_hash`), `token`, message. Automatically emits a partner invite when `partner_email` is provided.
- `POST /api/auth/login`  
  **Body:** `email`, `password`.  
  **Response:** `user`, JWT `token`, success message.
- `GET /api/auth/profile` *(JWT required)*  
  Returns sanitized user profile (`_id`, `name`, `email`, `partner_status`, etc.).
- `PUT /api/auth/profile` *(JWT)*  
  **Body:** `name`. Updates display name.
- `PUT /api/auth/notifications/email` *(JWT)*  
  **Body:** `enabled` (boolean). Toggles partner email alerts.
- `PUT /api/auth/password` *(JWT)*  
  **Body:** `current_password`, `new_password`. Re-hashes and stores password.
- Partner management *(JWT)*  
  - `GET /partner/status` → current `partner_status`, partner info, pending invites.  
  - `POST /partner/invite` **Body:** `partner_email`.  
  - `POST /partner/accept` / `POST /partner/reject` **Body:** `invitation_id`.

## Core Logic Flow
1. **Identity** — `create_access_token(identity=user["_id"])` encodes the Mongo ID; `get_jwt_identity()` retrieves it downstream.
2. **Persistence** — `User.create` hashes passwords, defaulting `email_notifications=True`. `User.update` writes partial updates via `$set`.
3. **Partner lifecycle** — `PartnerService` enforces invariants (no self invites, prevent duplicates, ensure single partner) and syncs both user documents on acceptance. Email sending is best-effort.

## How It Enables Other APIs
- The JWT produced here is mandatory for Daily Question, Quiz, Messages, and Calendar routes.
- `partner_id` and `partner_status` set by `PartnerService` unlock automatic receiver resolution in the Messages and Calendar services.
- Email notification preferences inform Messages scheduling and partner invite emails.

## Why Use These Endpoints
They establish the security boundary, maintain the canonical user document, and coordinate all partner-related workflows. Without them, other features cannot safely infer identity or relationship state.

## If You’re Stuck
- Inspect controller handlers in `api-container/app/controllers/auth_controller.py`.
- Trace business rules in `api-container/app/services/auth_service.py` and `partner_service.py`.
- Review JWT config in `api-container/app/config.py` for token expiry and secrets.
- Refresh on [Flask-JWT-Extended patterns](https://flask-jwt-extended.readthedocs.io/en/stable/basic_usage.html) for decorator behavior.
