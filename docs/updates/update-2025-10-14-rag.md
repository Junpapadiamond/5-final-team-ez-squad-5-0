# Update — 2025-10-14 (AgentOps RAG Foundation)

## What Shipped
- **RetrievalService** now lives beside the orchestrator (`app/services/retrieval_service.py`). It speaks Atlas Vector Search when available, falls back to cosine scoring, blends deterministic playbook tips, and caches results in Redis so AgentOps can fetch context in <500 ms.
- **LLM prompt upgrades** inject “# Retrieved Insights” into tone, coaching, and action prompts, giving OpenAI the exact markdown snippets it should cite. Responses carry `retrieval_sources` in their metadata for UI badges and audit logs.
- **AgentOrchestrator integration** threads `RetrievalService.fetch_context(...)` through analyze, coach, and plan flows, automatically crafting query text from daily questions, message history, and event payloads.
- **Ingestion pipeline** (`scripts/ingest_rag.py`) walks `docs/`, chunks sections (~400 tokens), redacts emails, embeds with `text-embedding-3-large`, and upserts vectors into the `agent_embeddings` collection with version tags and optional pruning.

## How To Use It
1. **Set environment flags**
   ```env
   RAG_FEATURE_FLAG=1
   RAG_VECTOR_BACKEND=atlas  # or pgvector for fallback
   RAG_EMBEDDING_COLLECTION=agent_embeddings
   RAG_PLAYBOOK_COLLECTION=agent_playbooks
   REDIS_URL=redis://localhost:6379/0
   OPENAI_EMBEDDING_MODEL=text-embedding-3-large
   ```
2. **Ingest the knowledge base**
   ```bash
   RAG_FEATURE_FLAG=1 python scripts/ingest_rag.py --version "$(date +%Y%m%d%H%M%S)" --prune
   ```
   Atlas Vector Search users must provision an index (default name `agent_embeddings_index`) with `embedding` as the vector field.
3. **Run the stack**. With Redis and Mongo up, the Agent page will surface retrieved citations under model outputs once `RAG_FEATURE_FLAG` is true.

## Safety & Monitoring
- All ingestion passes through `sanitize_text`, stripping emails and compressing whitespace before embeddings are generated.
- Slow or failed retrieval attempts fall back to the previous heuristic logic and log warnings (`app/services/retrieval_service.py:120`).
- New pytest suite (`tests/test_retrieval_service.py`) covers cosine fallback and ensures orchestrator passes chunk IDs downstream.

## Next Steps
- Populate the `agent_playbooks` collection with curated tips to mix deterministic guidance with semantic matches.
- Wire production Atlas Vector Search or pgvector credentials into deployment secrets and add health checks for Redis connectivity.
- Instrument dashboards for retrieval hit/miss counts and model latency so we can tune chunk sizes and cache TTLs post-rollout.
