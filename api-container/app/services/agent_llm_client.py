from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


_LLM_BACKOFF_UNTIL: Optional[datetime] = None


def _is_enabled() -> bool:
    flag = os.getenv("AGENT_LLM_ENABLED", "1")
    if flag.lower() in {"0", "false", "no"}:
        return False
    if _LLM_BACKOFF_UNTIL and datetime.utcnow() < _LLM_BACKOFF_UNTIL:
        return False
    return OpenAIClient.is_available()


def _backoff() -> None:
    global _LLM_BACKOFF_UNTIL
    seconds = max(5, int(os.getenv("AGENT_LLM_BACKOFF_SECONDS", "60")))
    _LLM_BACKOFF_UNTIL = datetime.utcnow() + timedelta(seconds=seconds)


class AgentLLMClient:
    """Wrapper around OpenAI Responses API for structured Together Agent outputs."""

    REQUEST_TIMEOUT_SECONDS = float(os.getenv("AGENT_LLM_REQUEST_TIMEOUT", "6"))

    TONE_SCHEMA: Dict[str, Any] = {
        "name": "ToneAnalysis",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "negative", "mixed"],
                },
                "confidence": {"type": "number"},
                "tone_summary": {"type": "string"},
                "emotional_drivers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "coaching_tips": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "suggested_reply": {"type": "string"},
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
            "required": ["sentiment", "confidence", "tone_summary", "coaching_tips", "strengths"],
        },
    }

    SUGGESTIONS_SCHEMA: Dict[str, Any] = {
        "name": "AgentSuggestions",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"},
                            "call_to_action": {"type": "string"},
                            "suggested_message": {"type": "string"},
                        },
                        "required": ["type", "title", "summary"],
                    },
                    "default": [],
                }
            },
            "required": ["suggestions"],
        },
    }

    STYLE_SCHEMA: Dict[str, Any] = {
        "name": "StyleSummary",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "style_summary": {"type": "string"},
                "key_traits": {"type": "array", "items": {"type": "string"}, "default": []},
                "signature_examples": {"type": "array", "items": {"type": "string"}, "default": []},
            },
            "required": ["style_summary"],
        },
    }

    ACTION_PLAN_SCHEMA: Dict[str, Any] = {
        "name": "AgentActionPlans",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "action_type": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"},
                            "requires_approval": {"type": "boolean"},
                            "call_to_action": {"type": "string"},
                            "suggested_message": {"type": "string"},
                            "follow_up_question": {"type": "string"},
                            "notes": {"type": "string"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["action_type", "title", "summary"],
                    },
                    "default": [],
                },
                "strategy": {"type": "string"},
                "explanation": {"type": "string"},
            },
            "required": ["actions"],
        },
    }

    @staticmethod
    def analyze_tone(
        message: str,
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not message or not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_TONE", os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"))
        prompt = AgentLLMClient._build_tone_prompt(message, context, retrieval)

        if AgentLLMClient._supports_responses(client):
            response = AgentLLMClient._responses_create(
                client,
                model=model,
                input=prompt,
                max_output_tokens=int(os.getenv("AGENT_TONE_MAX_TOKENS", "320")),
                response_format={"type": "json_schema", "json_schema": AgentLLMClient.TONE_SCHEMA},
            )
            payload = AgentLLMClient._extract_json(response)
            normalised = AgentLLMClient._normalise_tone_payload(
                payload,
                draft_message=message,
            )
            if normalised is not None:
                normalised["model"] = model
                normalised["raw"] = payload
                normalised["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
            return normalised

        # Fallback to chat completions emitting JSON
        system_prompt = (
            "You are the Together relationship agent. Respond strictly with JSON matching the schema."
        )
        payload = AgentLLMClient._chat_completion_json(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        if payload:
            normalised = AgentLLMClient._normalise_tone_payload(
                payload,
                draft_message=message,
            )
            if normalised is not None:
                normalised["model"] = model
                normalised["raw"] = payload
                normalised["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
            return normalised
        return None

    @staticmethod
    def plan_coaching(
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_COACHING", "gpt-4o-mini")
        prompt = AgentLLMClient._build_coaching_prompt(context, retrieval)
        package: Dict[str, Any] = {"model": model}

        if AgentLLMClient._supports_responses(client):
            response = AgentLLMClient._responses_create(
                client,
                model=model,
                input=prompt,
                max_output_tokens=int(os.getenv("AGENT_COACHING_MAX_TOKENS", "480")),
                response_format={"type": "json_schema", "json_schema": AgentLLMClient.SUGGESTIONS_SCHEMA},
            )
            payload = AgentLLMClient._extract_json(response)
            if isinstance(payload, dict):
                package["cards"] = AgentLLMClient._normalise_suggestions(payload.get("suggestions") or [])
                package["strategy"] = AgentLLMClient._to_text(payload.get("strategy"))
                package["explanation"] = AgentLLMClient._to_text(payload.get("explanation"))
                package["raw"] = payload
                package["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
                return package
            if response is not None:
                logger.warning("Agent coaching suggestion generation returned unexpected payload")

        system_prompt = (
            "You are the Together coaching planner. Respond strictly with JSON matching the schema."
        )
        payload = AgentLLMClient._chat_completion_json(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        if isinstance(payload, dict):
            package["cards"] = AgentLLMClient._normalise_suggestions(payload.get("suggestions") or [])
            package["strategy"] = AgentLLMClient._to_text(payload.get("strategy"))
            package["explanation"] = AgentLLMClient._to_text(payload.get("explanation"))
            package["raw"] = payload
            package["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
            return package
        return None

    @staticmethod
    def plan_actions(
        event: Dict[str, Any],
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_ACTIONS", os.getenv("AGENT_MODEL_COACHING", "gpt-4o-mini"))
        prompt = AgentLLMClient._build_action_prompt(event, context, retrieval)
        package: Dict[str, Any] = {"model": model}

        if AgentLLMClient._supports_responses(client):
            response = AgentLLMClient._responses_create(
                client,
                model=model,
                input=prompt,
                max_output_tokens=int(os.getenv("AGENT_ACTION_MAX_TOKENS", "640")),
                response_format={"type": "json_schema", "json_schema": AgentLLMClient.ACTION_PLAN_SCHEMA},
            )
            payload = AgentLLMClient._extract_json(response)
            if isinstance(payload, dict):
                package["actions"] = AgentLLMClient._normalise_actions(payload.get("actions") or [])
                package["strategy"] = AgentLLMClient._to_text(payload.get("strategy"))
                package["explanation"] = AgentLLMClient._to_text(payload.get("explanation"))
                package["raw"] = payload
                package["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
                return package
            if response is not None:
                logger.warning("Agent action planning returned unexpected payload")

        system_prompt = (
            "You are the Together relationship agent. Respond strictly with JSON matching the schema."
        )
        payload = AgentLLMClient._chat_completion_json(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        if isinstance(payload, dict):
            package["actions"] = AgentLLMClient._normalise_actions(payload.get("actions") or [])
            package["strategy"] = AgentLLMClient._to_text(payload.get("strategy"))
            package["explanation"] = AgentLLMClient._to_text(payload.get("explanation"))
            package["raw"] = payload
            package["retrieval_sources"] = AgentLLMClient._extract_retrieval_sources(retrieval)
            return package
        return None

    @staticmethod
    def summarize_style(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_STYLE", "gpt-4o-mini")
        prompt = AgentLLMClient._build_style_prompt(context)

        if AgentLLMClient._supports_responses(client):
            response = AgentLLMClient._responses_create(
                client,
                model=model,
                input=prompt,
                max_output_tokens=int(os.getenv("AGENT_STYLE_MAX_TOKENS", "320")),
                response_format={"type": "json_schema", "json_schema": AgentLLMClient.STYLE_SCHEMA},
            )
            payload = AgentLLMClient._extract_json(response)
            if payload is not None:
                return AgentLLMClient._normalise_style_payload(payload)

        system_prompt = (
            "You are the Together communication analyst. Respond strictly with JSON matching the schema."
        )
        payload = AgentLLMClient._chat_completion_json(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        if isinstance(payload, dict):
            return AgentLLMClient._normalise_style_payload(payload)
        return None

    @staticmethod
    def _extract_json(response: Any) -> Optional[Dict[str, Any]]:
        if not response or not getattr(response, "output", None):
            return None

        try:
            first_item = response.output[0]
            content = getattr(first_item, "content", None)
            if not content:
                return None
            text = content[0].text
            return json.loads(text)
        except Exception as exc:
            logger.warning("Failed to parse LLM JSON payload: %s", exc)
            return None

    @staticmethod
    def _supports_responses(client: Any) -> bool:
        return hasattr(client, "responses")

    @staticmethod
    def _responses_create(client: Any, **kwargs) -> Optional[Any]:
        if not AgentLLMClient._supports_responses(client):
            return None

        resource = client.responses
        timeout = AgentLLMClient.REQUEST_TIMEOUT_SECONDS
        try:
            if hasattr(resource, "with_options"):
                resource = resource.with_options(timeout=timeout)
                return resource.create(**kwargs)
            return resource.create(timeout=timeout, **kwargs)
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Agent LLM responses call failed: %s", exc)
            _backoff()
            return None

    @staticmethod
    def _chat_completion_json(
        *,
        client: Any,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[Dict[str, Any]]:
        if not hasattr(client, "chat"):
            return None

        try:
            completions = client.chat.completions
            timeout = AgentLLMClient.REQUEST_TIMEOUT_SECONDS
            if hasattr(completions, "with_options"):
                completions = completions.with_options(timeout=timeout)
                completion = completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=int(os.getenv("AGENT_CHAT_JSON_MAX_TOKENS", "480")),
                    response_format={"type": "json_object"},
                )
            else:
                completion = completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=int(os.getenv("AGENT_CHAT_JSON_MAX_TOKENS", "480")),
                    response_format={"type": "json_object"},
                    timeout=timeout,
                )

            message = completion.choices[0].message
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return json.loads(content)
            if isinstance(content, list) and content:
                first = content[0]
                text = first.get("text") if isinstance(first, dict) else None
                if text:
                    return json.loads(text)
            return None
        except Exception as exc:  # pragma: no cover
            logger.warning("Agent chat JSON completion failed: %s", exc)
            _backoff()
            return None

    @staticmethod
    def _to_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, dict):
            for key in ("label", "text", "value"):
                if key in value and isinstance(value[key], str):
                    return value[key]
            for key in ("label", "summary"):
                if key in value and not isinstance(value[key], str):
                    nested = AgentLLMClient._to_text(value[key])
                    if nested:
                        return nested
        if isinstance(value, list):
            flattened = [AgentLLMClient._to_text(item) for item in value]
            flattened = [item for item in flattened if item]
            if flattened:
                return "; ".join(flattened)
        try:
            return json.dumps(value)
        except Exception:
            return str(value)

    @staticmethod
    def _normalise_confidence(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            for key in ("score", "confidence", "value"):
                if key in value and isinstance(value[key], (int, float)):
                    return float(value[key])
        return None

    @staticmethod
    def _normalise_bool(value: Any, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1"}:
                return True
            if lowered in {"false", "no", "0"}:
                return False
        if isinstance(value, (int, float)):
            return value != 0
        return default

    @staticmethod
    def _normalise_suggestions(raw: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            card: Dict[str, Any] = dict(item)
            card["id"] = AgentLLMClient._to_text(card.get("id")) or f"suggestion-{idx}"
            card["type"] = AgentLLMClient._to_text(card.get("type")) or "custom"
            card["title"] = AgentLLMClient._to_text(card.get("title")) or "Agent suggestion"
            card["summary"] = AgentLLMClient._to_text(card.get("summary")) or ""
            card["confidence"] = AgentLLMClient._normalise_confidence(card.get("confidence"))
            payload = card.get("payload")
            if isinstance(payload, dict):
                card["payload"] = {
                    key: AgentLLMClient._to_text(value)
                    for key, value in payload.items()
                    if AgentLLMClient._to_text(value)
                }
            else:
                card["payload"] = {}
            normalised.append(card)
        return normalised

    @staticmethod
    def _normalise_actions(raw: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            action: Dict[str, Any] = dict(item)
            action["id"] = AgentLLMClient._to_text(action.get("id")) or f"action-{idx}"
            action["action_type"] = AgentLLMClient._to_text(action.get("action_type")) or ""
            action["title"] = AgentLLMClient._to_text(action.get("title")) or action["action_type"].replace("_", " ").title()
            action["summary"] = AgentLLMClient._to_text(action.get("summary")) or action["title"]
            action["confidence"] = AgentLLMClient._normalise_confidence(action.get("confidence"))
            action["requires_approval"] = AgentLLMClient._normalise_bool(action.get("requires_approval"), True)
            for key in ("call_to_action", "suggested_message", "follow_up_question", "notes", "rationale"):
                if key in action:
                    coerced = AgentLLMClient._to_text(action.get(key))
                    action[key] = coerced if coerced else None
            actions.append(action)
        return actions

    @staticmethod
    def _normalise_tone_payload(
        payload: Optional[Dict[str, Any]],
        *,
        draft_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        normalised = dict(payload)
        normalised["sentiment"] = AgentLLMClient._to_text(normalised.get("sentiment")) or "neutral"
        normalised["tone_summary"] = AgentLLMClient._to_text(normalised.get("tone_summary")) or ""
        suggested_reply = AgentLLMClient._to_text(normalised.get("suggested_reply"))
        normalised["suggested_reply"] = AgentLLMClient._coerce_sender_reply(
            suggested_reply,
            draft_message=draft_message,
        )
        normalised["confidence"] = AgentLLMClient._normalise_confidence(normalised.get("confidence")) or 0.0
        normalised["warnings"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("warnings", []) or []
            if AgentLLMClient._to_text(item)
        ]
        normalised["strengths"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("strengths", []) or []
            if AgentLLMClient._to_text(item)
        ]
        normalised["coaching_tips"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("coaching_tips", []) or []
            if AgentLLMClient._to_text(item)
        ]
        normalised["emotional_drivers"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("emotional_drivers", []) or []
            if AgentLLMClient._to_text(item)
        ]
        return normalised

    @staticmethod
    def _normalise_style_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        normalised = dict(payload)
        normalised["style_summary"] = AgentLLMClient._to_text(normalised.get("style_summary")) or ""
        normalised["key_traits"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("key_traits", []) or []
            if AgentLLMClient._to_text(item)
        ]
        normalised["signature_examples"] = [
            AgentLLMClient._to_text(item) or ""
            for item in normalised.get("signature_examples", []) or []
            if AgentLLMClient._to_text(item)
        ]
        return normalised

    @staticmethod
    def _build_tone_prompt(
        message: str,
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        partner_context = context.get("partner_status", "unknown")
        style_summary = context.get("style_profile", {}).get("style_summary")
        recent_messages = context.get("recent_messages", [])

        parts = [
            "You are the Together relationship agent. Analyse the draft and respond with compact JSON (keep strings short).",
            f"Partner status: {partner_context}",
        ]
        if style_summary:
            parts.append(f"User style profile summary: {style_summary}")

        if recent_messages:
            formatted_messages = "\n".join(
                f"- {item.get('author', 'User')}: {item.get('content')}"
                for item in recent_messages[:5]
            )
            parts.append("Recent message history:\n" + formatted_messages)

        parts.append("Draft message:\n" + message)
        retrieved_block = AgentLLMClient._render_retrieved_insights(retrieval)
        if retrieved_block:
            parts.append(retrieved_block)
        parts.append(
            "Return JSON with sentiment (positive/neutral/negative/mixed), confidence (0-1), short tone_summary, strengths[], coaching_tips[], emotional_drivers[], optional suggested_reply, warnings[] (omit when empty). Keep each string under 160 characters. The suggested_reply must be an improved version of the user's draft that they can send next. Keep the sender's first-person perspective, reuse any facts already shared, and never role-play the partner. Do not invent personal status updates about the sender (for example \"I'm good\") unless the draft already makes that claim. If you need to add warmth, do it with appreciation, encouragement, or a light question."
        )

        return "\n\n".join(parts)

    @staticmethod
    def _render_retrieved_insights(retrieval: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        if not retrieval:
            return None
        lines: List[str] = ["# Retrieved Insights"]
        for item in retrieval:
            snippet = item.get("prompt_snippet") or item.get("content")
            citation = item.get("citation")
            if snippet:
                lines.append(f"- {snippet}")
            elif citation:
                lines.append(f"- {citation}")
        return "\n".join(lines) if len(lines) > 1 else None

    @staticmethod
    def _extract_retrieval_sources(retrieval: Optional[List[Dict[str, Any]]]) -> List[str]:
        if not retrieval:
            return []
        sources: List[str] = []
        for item in retrieval:
            chunk_id = item.get("chunk_id")
            if chunk_id:
                sources.append(str(chunk_id))
        return sources

    @staticmethod
    def _coerce_sender_reply(
        reply: Optional[str],
        *,
        draft_message: Optional[str] = None,
    ) -> Optional[str]:
        if not reply:
            return None

        cleaned = reply.strip().strip('"').strip()
        if not cleaned:
            return None

        if draft_message:
            draft = draft_message.strip().strip('"').strip()
        else:
            draft = ""

        lower = cleaned.lower()

        disallowed_prefixes = (
            "i'm good",
            "i am good",
            "i'm doing well",
            "i am doing well",
            "hi i'm good",
            "hi i am good",
            "i'm great",
            "i am great",
        )
        if draft:
            draft_lower = draft.lower()
            if any(prefix in lower for prefix in disallowed_prefixes) and not any(
                prefix in draft_lower for prefix in disallowed_prefixes
            ):
                # Replace the leading personal status with a neutral acknowledgement that keeps momentum.
                for prefix in disallowed_prefixes:
                    if lower.startswith(prefix):
                        cleaned = cleaned[len(prefix) :].lstrip(", ").lstrip()
                        break
                cleaned = f"{draft} {cleaned}".strip()

        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."

        return cleaned

    @staticmethod
    def _build_coaching_prompt(
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        partner_context = context.get("partner_status", "unknown")
        question = context.get("daily_question")
        events = context.get("upcoming_events", [])
        recent_messages = context.get("recent_messages", [])

        parts = [
            "You are the Together coaching planner. Produce 1-2 concise suggestion cards as JSON.",
            f"Partner status: {partner_context}",
        ]

        if question:
            parts.append(f"Today's shared reflection question: {question.get('question')}")
            if question.get("your_answer"):
                parts.append(f"User answered: {question['your_answer']}")
            if question.get("partner_answer"):
                parts.append(f"Partner answered: {question['partner_answer']}")

        if events:
            upcoming = "\n".join(
                f"- {item.get('title')} on {item.get('start_time')}"
                for item in events[:5]
            )
            parts.append("Upcoming events:\n" + upcoming)

        if recent_messages:
            formatted_messages = "\n".join(
                f"- {item.get('author', 'User')}: {item.get('content')}"
                for item in recent_messages[:5]
            )
            parts.append("Recent messages:\n" + formatted_messages)

        retrieved_block = AgentLLMClient._render_retrieved_insights(retrieval)
        if retrieved_block:
            parts.append(retrieved_block)
        parts.append(
            "Each card requires: type keyword (message_draft/daily_question/calendar/custom), short title, summary (<=200 chars), optional confidence (0-1), optional call_to_action, optional suggested_message (<=200 chars)."
        )

        return "\n\n".join(parts)

    @staticmethod
    def _build_action_prompt(
        event: Dict[str, Any],
        context: Dict[str, Any],
        retrieval: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        event_type = event.get("event_type")
        scenario = event.get("scenario") or "daily_check_in"
        payload = event.get("payload") or {}
        partner_context = context.get("partner_status", "unknown")

        parts = [
            "You are the Together relationship agent. Given the new activity, outline the next best actions as JSON.",
            f"Event type: {event_type}",
            f"Workflow scenario: {scenario}",
            f"Partner status: {partner_context}",
        ]

        if payload:
            serialized_payload = json.dumps(payload, ensure_ascii=False, default=str)[:800]
            parts.append(f"Event payload: {serialized_payload}")

        daily = context.get("daily_question")
        if daily:
            parts.append(
                "Daily question context: "
                + json.dumps(
                    {
                        "question": daily.get("question"),
                        "your_answer": daily.get("your_answer"),
                        "partner_answer": daily.get("partner_answer"),
                        "answered": daily.get("answered"),
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )

        messages = context.get("recent_messages") or []
        if messages:
            formatted_messages = "\n".join(
                f"- {item.get('author', 'User')}: {item.get('content')}"
                for item in messages[:5]
            )
            parts.append("Recent messages:\n" + formatted_messages)

        events = context.get("upcoming_events") or []
        if events:
            formatted_events = "\n".join(
                f"- {item.get('title')} at {item.get('start_time')}"
                for item in events[:5]
            )
            parts.append("Upcoming events:\n" + formatted_events)

        style_summary = (context.get("style_profile") or {}).get("style_summary")
        if style_summary:
            parts.append(f"User style summary: {style_summary}")

        retrieved_block = AgentLLMClient._render_retrieved_insights(retrieval)
        if retrieved_block:
            parts.append(retrieved_block)
        parts.append(
            "Return JSON matching the provided schema. Each action should include action_type, title, summary, optional confidence (0-1), requires_approval (boolean), optional call_to_action (<=120 chars), optional suggested_message (<=220 chars), optional follow_up_question, optional notes, optional rationale. Prefer 1-2 focused actions that feel grounded in the context. Keep language warm, supportive, and concise."
        )

        return "\n\n".join(parts)

    @staticmethod
    def _build_style_prompt(context: Dict[str, Any]) -> str:
        samples = context.get("message_samples", [])
        if not samples:
            return ""

        snippet = "\n".join(f"- {sample}" for sample in samples[:10])

        return (
            "You are analysing a collection of messages to describe the author's communication style.\n"
            "Provide a concise summary (<=180 chars) capturing tone, pacing, emoji usage, and notable traits.\n"
            "Return JSON with style_summary, optional key_traits[], optional signature_examples[] (each <=140 chars).\n"
            "Message samples:\n"
            f"{snippet}"
        )
