# Bug Summary 1 – OpenAI Tone Feedback Failure

## What Happened
- API requests to `/api/agent/analyze` returned `llm_feedback: null` and eventually raised a 500.
- Container logs showed `TypeError: __init__() got an unexpected keyword argument 'proxies'` from `openai_client.py`.

## Root Cause
- The Docker image carried an older `httpx` package that lacks support for the `proxies` keyword now used by `openai>=1.35`.
- Because the dependency was cached during previous builds, the `httpx>=0.27.0` constraint in `requirements.txt` was not enforced, leaving the stale version in place.

## Fix Applied
- Exported `OPENAI_API_KEY` into a project-level `.env` so the container receives the key on startup.
- Rebuilt the API image (or ran `pip install --upgrade 'httpx>=0.27.0'`) to ensure `httpx` 0.27+ installs alongside `openai`.
- Restarted the stack with `docker compose up -d` so the refreshed dependencies and env vars take effect.

## Validation
- Re-ran the analyze endpoint with `curl -X POST http://localhost:5001/api/agent/analyze ...`; response now includes populated `llm_feedback`.
- Monitored `docker compose logs -f api` and confirmed the OpenAI traceback no longer appears.

## Follow-Ups
- Rotate the exposed OpenAI key and store future secrets in `.env` / secret manager.
- Consider pinning `httpx` to an exact version (e.g., `httpx==0.27.0`) and enabling CI tests that exercise the OpenAI client with a mocked response to catch dependency regressions sooner.
