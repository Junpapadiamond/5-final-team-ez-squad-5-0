Integration / Auth Fix Report
================================

Context
-------
- The project is split into multiple containers (`api-container`, `frontend`, `db-container`, `web-container`, worker) orchestrated by `docker-compose.yml`.
- The React/Next.js frontend (port 3000) talks to the Flask API on port 5001 using JWT bearer tokens stored in local storage.
- Authentication endpoints live under `api-container/app/controllers/auth_controller.py`; persistence is handled via `User` in `api-container/app/models/user.py`.

Issue Found
-----------
- Registration and login requests were failing with HTTP 500 because MongoDB documents include `datetime` objects (`created_at`) that Flask's `jsonify` cannot serialize.
- The same documents can also contain `ObjectId` instances (`_id`, `partner_id`, etc.). When returned directly to the client they lead to serialization errors or unusable payloads.
- Because the API response never reached the browser, the frontend appeared to be "disconnected" from the backend even when the network path was correct.

Fix Implemented
---------------
- Added a centralized `User.serialize` helper that safely transforms MongoDB user documents by:
  - Converting `_id` and any other `ObjectId` values to strings.
  - Converting `datetime` values to ISO 8601 strings.
- Updated `find_by_email`, `find_by_id`, and `create` to always return serialized user payloads, ensuring every auth response is JSON-safe.
- Confirmed serialization manually (`python` script) so `json.dumps(User.serialize(user))` succeeds without errors.
- Updated the Next.js API client (`frontend/src/lib/api.ts`) to default browser calls to a same-origin `/api` base (adjusting baseURL at runtime if a server-rendered instance leaks through) and added a rewrite in `next.config.ts` so `/api/*` requests made from the browser are proxied by the frontend container to the Flask API service when running under Docker Compose.
- Removed the `NEXT_PUBLIC_API_URL` override in `docker-compose.yml` so the production bundle no longer hard-codes `http://api:5001` and instead uses the new same-origin proxy path.
- Restored `api-container/app/services/__init__.py` to export the service layer modules, removing stray text that was breaking the API container start-up.

Current Behaviour
-----------------
- `/api/auth/register` now responds with a 201 containing `{ user, token, message }` where `user.created_at` is an ISO string and no backend exception is thrown.
- `/api/auth/login` returns 200 with the same structure, allowing the frontend's axios client to store the token and transition to the dashboard.
- These fixes apply automatically inside Docker because the code changes are part of the API container image build.

Outstanding Risks & Follow-ups
------------------------------
- Outbound email features (partner invites, reminders) still require valid SMTP credentials (`MAIL_USERNAME`, `MAIL_PASSWORD`) — without them the worker will log failures (exceptions are currently swallowed).
- Override `NEXT_PUBLIC_API_URL` (build-time) if the public site is not served from the same host/ports as the API, or adjust the new rewrite target via `INTERNAL_API_URL` so the proxy still reaches the Flask service.
- Other collections (events, messages, daily questions) already format their timestamps, but future endpoints should reuse the same serialization pattern to avoid regressions.
- No automated auth tests exist; adding API tests that hit `/api/auth/register` and `/api/auth/login` would prevent reintroducing the datetime/ObjectId regression.

Next Validation Steps
---------------------
1. `docker compose up --build` to rebuild the API container and confirm login/register succeed through the browser.
2. Seed/test MongoDB data if necessary; the application expects the `together` database that ships with the compose stack.
3. Optionally extend the shared serializer approach to other models if more complex documents begin surfacing in API responses.
