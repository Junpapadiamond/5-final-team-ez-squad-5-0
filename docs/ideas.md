# Product & AI Enhancement Ideas

## 1. Chat Style Mimic with Voice Layer
- **Concept:** Teach the agent each partner’s textual voice (tone, emojis, cadence) and optionally add a voice experience where the system generates TTS messages in the partner’s voice.
- **Components:**
  - **Messaging embeddings** for style cues (existing Agent/RAG Phase 1 groundwork).
  - **Prompting layer** that injects retrieved style snippets when drafting messages.
  - **Voice mode (stretch):**
    - Collect 30s user voice sample with consent.
    - Use state-of-the-art voice cloning (e.g., OpenAI Voice, ElevenLabs) for TTS; add ASR for mirrored responses.
  - **Risks:** Voice cloning carries higher privacy/regulatory concerns; requires opt-in, secure storage, and clear disclosures.
- **Status:** Fits naturally into Agent/RAG Phase 2 once basic RAG retrieval exists. Voice clone extension would be a later milestone after policy/legal review.

## 2. Daily Engagement Copilot (Roadmap Base Feature)
- **Concept (already in Agent_RAG_Implementation):** An agent monitors daily activity (questions answered, quiz progress, messages) and nudges next-best actions.
- **Enhancements:**
  - Add mood signals or context (see Symptom Tracker discussion).
  - Provide quick scheduling or message drafts with a “send with my tone” option.
- **Priority:** High – lays foundation for all other AI experiences; currently Phase 2 in the roadmap.

## 3. Symptom Tracker & AI Emotional Understanding
- **Concept:** Let users log physical/emotional symptoms or automatically infer from patterns; the agent suggests empathetic responses or check-ins.
- **Components:**
  - Symptom logging UI + data schema (`symptom_logs`).
  - Optional integrations (cycle tracking, sentiment analysis on daily answers/messages).
  - RAG over curated wellness guidance to suggest supportive actions.
- **Risks:** Health-related data needs strict consent, storage, and disclaimers (not medical advice).
- **Status:** Medium-term stretch (Phase 3+). Requires policy approval and careful UX copy.

## 4. Timed Creative Messages (Drawings/Cards/Media)
- **Concept:** Allow users to create creative assets (handwritten cards, doodles, photos, short videos) and schedule them like messages.
- **Implementation thoughts:**
  - Extend scheduled messages schema to store media references (S3/GCS).
  - Provide canvas editor or integration with handwriting/notes-style input (e.g., use Fabric.js on frontend).
  - For “AI handwriting”, integrate a handwriting synthesis API or generate SVG paths mimicking custom styles.
- **Voice tie-in:** Could pair with TTS for a narrated card.
- **Status:** High appeal for long-distance couples; mostly product/UX work plus storage considerations. Less dependent on Agent/RAG.

## 5. Handwritten Card Generator
- **Concept:** Users type messages and the system renders them in a realistic handwritten style (maybe based on partner’s handwriting sample).
- **Approach Options:**
  - Collect handwriting samples, train or finetune a handwriting model (e.g., GAN-based).
  - Use existing APIs (Calligraphr, Scribble) or font generation tools.
  - Export to PDF/PNG and attach to messages or allow digital “unwrapping.”
- **Status:** Feasible without heavy AI infra; can ride on the Timed Creative Messages effort.

## 6. Voice Wake-Up Companion
- **Concept:** Partner records short greetings; agent schedules/plays them when partner wakes. Optional AI fallback if no fresh recording.
- **Dependencies:** TTS/Voice clone channels from idea #1, scheduler from Messages service.
- **Status:** Good follow-on once voice infrastructure exists; can be a distinct product surface (“Morning voice notes”).

## Prioritization Snapshot
1. **Daily Engagement Copilot** – already planned; unlocks most subsequent features.
2. **Chat Style Mimic (text first)** – build on RAG retrieval to offer tone-aware drafts.
3. **Timed Creative Messages + Handwritten Cards** – product differentiation with moderate tech lift.
4. **Voice Layer for Style Mimic** – high emotional impact but requires voice cloning safeguards.
5. **Symptom Tracker & Emotional Understanding** – long-term vision contingent on privacy/compliance readiness.

## Next Steps
- Integrate “Style Mimic Drafting” into Agent/RAG Phase 2 backlog (text-only to start).
- Spec Timed Creative Messages architecture (media storage, editor UI, scheduling updates).
- If voice cloning is pursued, research compliant vendors and design consent flows before prototyping.
