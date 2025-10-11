# Agentic Workflow & RAG Integration Plan

## 1. Goals
- **Personalized guidance**: create an agent that reacts to user activity and suggests next-best actions (reminders, prompts, drafted messages).
- **Knowledge infusion**: empower the agent with Retrieval-Augmented Generation (RAG) so insights include historical context and curated resources.
- **Incremental rollout**: ship in stages that can be independently tested and reverted.

## 2. High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend & API Gateway                                                 │
│   - New endpoints: /api/agent/actions, /api/insights/query              │
└───────────────┬───────────────────────────────┬────────────────────────┘
                │                               │
        ┌───────▼────────┐                 ┌────▼─────────────────────┐
        │ Agent Service   │                 │ RAG Service              │
        │ (FastAPI/Flask) │                 │ (FastAPI/Flask)          │
        │  - Workflow SM  │                 │  - Embedding Producer    │
        │  - Action rules │                 │  - Vector Store adapter  │
        │  - LLM calls    │                 │  - Retrieval pipelines   │
        └───────┬─────────┘                 └──────────────┬──────────┘
                │                                          │
        ┌───────▼────────┐                 ┌───────────────▼──────────┐
        │ Mongo Change    │                 │ Vector DB (FAISS/Pinecone│
        │ Streams + Tasks │                 │ Weaviate)                │
        │ (Celery/RQ)     │                 │                          │
        └───────┬─────────┘                 └──────────────┬──────────┘
                │                                          │
        ┌───────▼────────────┐                     ┌───────▼───────────┐
        │ Existing MongoDB   │                     │ External Knowledge│
        │ collections        │                     │ Sources (Markdown,│
        │ (users, messages,  │                     │ curated tips)     │
        │ daily_questions…)  │                     └───────────────────┘
        └────────────────────┘
```

## 3. Phase Breakdown

### Phase 0 – Foundations (1 sprint)
1. **Data contracts**
   - Document schemas for `users`, `messages`, `daily_questions`, `quiz_responses`, `events`.
   - Add explicit consent flags (`agent_opt_in`, `rag_opt_in`) to user profiles.
2. **Instrumentation**
   - Enable MongoDB change streams or schedule cron-like jobs via Celery worker.
   - Expose lightweight internal API (`/api/internal/activity-feed`) returning recent activity for agent debugging.
3. **Dev infrastructure**
   - Introduce `.env.agent.example` covering LLM keys, vector DB credentials.
   - Add local docker-compose service for vector DB (FAISS container or Weaviate).

### Phase 1 – RAG Data Pipeline (1–2 sprints)
1. **Embedding generation**
   - Create `insights` service module with tasks to embed:
     - Daily answers (`question`, `answer`, `date`).
     - Quiz submissions (aggregate per question, optional).
     - Message summaries (see below).
   - Use background worker to create embeddings on insert/update.
2. **Vector store**
   - Implement adapter for chosen store (start with FAISS for local dev, abstract interface).
   - Store metadata (`user_id`, `partner_id`, `content_type`, timestamps, consent flags).
3. **Summarization jobs**
   - For long messages, run nightly batch that summarizes conversations before embedding to control token usage.
   - Persist summaries back to Mongo (`messages_summaries` collection) for reuse.
4. **RAG endpoint**
   - Add `/api/insights/query` (JWT protected) accepting `question`, optional `scope` (`daily`, `quiz`, `messages`, `tips`).
   - Pipeline: retrieve top-k vectors → construct prompt → call LLM → return formatted answer with citations.
5. **Testing & metrics**
   - Unit tests for embedding generator, vector store adapter, retrieval ordering.
   - Smoke test for end-to-end RAG endpoint using fake embeddings.
6. **Style fingerprint groundwork**
   - Generate lightweight linguistic profiles per user (emoji density, punctuation, exemplar messages).
   - Store refreshed summaries in `style_profiles` for later prompt conditioning.
   - Capture new user samples through `/api/agent/analyze` so tone learning improves with every draft.
   - When `OPENAI_API_KEY` is provided, augment the analysis with OpenAI's GPT models for richer tone feedback.

### Phase 2 – Agentic Workflow MVP (1 sprint)
1. **Workflow definition**
   - Model state machine with scenarios: `onboarding`, `daily_check_in`, `quiz_follow_up`, `anniversary_planning`.
   - Encode triggers (e.g., missed daily question for 2 days, quiz submitted, upcoming event).
2. **Action engine**
   - Agent service evaluates triggers via scheduled job.
   - Determine recommended actions:
     - Send reminder via Messages API.
     - Generate calendar suggestion using RAG context (“Plan something around your shared interest in hiking.”).
     - Draft supportive message using LLM with retrieved context and the stored style fingerprint.
   - Provide immediate feedback on drafted text via `/api/agent/analyze`, refreshing style fingerprints as users iterate.
3. **API surface**
   - `/api/agent/actions` GET → returns pending suggestions with metadata (`type`, `confidence`, `source_ids`).
   - `/api/agent/actions/<id>/execute` POST → user approval to send message or create event.
4. **Safeguards**
   - Log every agent decision to `agent_audit` collection.
   - Require explicit user confirmation before sending partner-facing content.
5. **UX Hooks**
   - Frontend notification surfaces new actions.
   - Add “teach the agent” button linking to knowledge base upload (future).

### Phase 3 – Enrichment & Automation (stretch)
1. **Partner-facing summaries**
   - Weekly digest summarizing both users’ reflections (with consent).
2. **External resources RAG**
   - Curate Markdown knowledge base (relationship tips, conflict resolution). Load into vector store.
3. **Feedback loop**
   - Collect user ratings on agent suggestions to fine-tune prompts/weights.
4. **Auto-execution rules**
   - Allow users to trust specific workflows (e.g., auto-remind if daily question missed >2 days).

## 4. Technical Decisions To Finalize
- **Vector database**: start with FAISS (self-hosted) vs managed Pinecone/Weaviate. Consider deployment constraints.
- **LLM provider**: OpenAI, Anthropic, or self-hosted (Llama 3). Evaluate latency, cost, token limits.
- **Worker framework**: Reuse existing Celery/RQ setup or introduce AWS Lambda/Temporal if scaling needs.
- **Security**: encrypt stored embeddings containing sensitive text; scope retrieval strictly by `user_id`.
- **Observability**: add structured logging + metrics (action throughput, retrieval latency, suggestion acceptance rate).

## 5. Dependencies & Risks
- Reliable Mongo change streams require replica set; otherwise rely on polling.
- Need user consent flow updates in frontend.
- LLM costs must be budgeted; add rate limiting and caching.
- Data quality (typos, sensitive content) may degrade results—consider redaction filters.
- Ensure GDPR-style data export/deletion covers new derived stores.

## 6. Deliverables Checklist
- [ ] Schema updates (`agent_opt_in`, `rag_opt_in`) + migrations.
- [ ] Vector DB container/service + config.
- [ ] Embedding pipeline with tests.
- [ ] `/api/insights/query` endpoint.
- [ ] Agent service with action state machine & APIs.
- [ ] Frontend surfaces (alerts, confirmations).
- [ ] Monitoring dashboards and audit logs.

## 7. Learning & Ramp-Up Resources
- MongoDB Change Streams: https://www.mongodb.com/docs/manual/changeStreams/
- Temporal vs Celery comparison: https://temporal.io/blog/temporal-vs-celery
- Open-source embedding models: https://huggingface.co/collections/sentence-transformers/all-minilm-64b-6639b43729ce4359dfeda80c
- RAG design patterns: https://www.promptingguide.ai/techniques/rag
- Responsible AI guidelines: review company policy + https://ai.google/responsibility/principles/
