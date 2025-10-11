from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional, Sequence

from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    flag = os.getenv("AGENT_LLM_ENABLED", "1")
    return flag.lower() not in {"0", "false", "no"} and OpenAIClient.is_available()


class AgentLLMClient:
    """Wrapper around OpenAI Responses API for structured Together Agent outputs."""

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

    @staticmethod
    def analyze_tone(message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not message or not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_TONE", os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"))
        prompt = AgentLLMClient._build_tone_prompt(message, context)

        if AgentLLMClient._supports_responses(client):
            try:
                response = client.responses.create(
                    model=model,
                    input=prompt,
                    max_output_tokens=int(os.getenv("AGENT_TONE_MAX_TOKENS", "320")),
                    response_format={"type": "json_schema", "json_schema": AgentLLMClient.TONE_SCHEMA},
                )
                payload = AgentLLMClient._extract_json(response)
                return AgentLLMClient._normalise_tone_payload(payload)
            except Exception as exc:  # pragma: no cover - network errors
                logger.warning("Agent tone analysis failed: %s", exc)
                return None

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
            return AgentLLMClient._normalise_tone_payload(payload)
        return None

    @staticmethod
    def plan_coaching(context: Dict[str, Any]) -> Optional[Sequence[Dict[str, Any]]]:
        if not _is_enabled():
            return None

        client = OpenAIClient.get_client()
        if client is None:
            return None

        model = os.getenv("AGENT_MODEL_COACHING", "gpt-4o-mini")
        prompt = AgentLLMClient._build_coaching_prompt(context)

        if AgentLLMClient._supports_responses(client):
            try:
                response = client.responses.create(
                    model=model,
                    input=prompt,
                    max_output_tokens=int(os.getenv("AGENT_COACHING_MAX_TOKENS", "480")),
                    response_format={"type": "json_schema", "json_schema": AgentLLMClient.SUGGESTIONS_SCHEMA},
                )
                payload = AgentLLMClient._extract_json(response)
                if isinstance(payload, dict):
                    return AgentLLMClient._normalise_suggestions(payload.get("suggestions") or [])
                return None
            except Exception as exc:  # pragma: no cover
                logger.warning("Agent coaching suggestion generation failed: %s", exc)
                return None

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
            return AgentLLMClient._normalise_suggestions(payload.get("suggestions") or [])
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
            try:
                response = client.responses.create(
                    model=model,
                    input=prompt,
                    max_output_tokens=int(os.getenv("AGENT_STYLE_MAX_TOKENS", "320")),
                    response_format={"type": "json_schema", "json_schema": AgentLLMClient.STYLE_SCHEMA},
                )
                payload = AgentLLMClient._extract_json(response)
                return AgentLLMClient._normalise_style_payload(payload)
            except Exception as exc:  # pragma: no cover
                logger.warning("Agent style summary generation failed: %s", exc)
                return None

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
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens= int(os.getenv("AGENT_CHAT_JSON_MAX_TOKENS", "480")),
                response_format={"type": "json_object"},
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
    def _normalise_tone_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        normalised = dict(payload)
        normalised["sentiment"] = AgentLLMClient._to_text(normalised.get("sentiment")) or "neutral"
        normalised["tone_summary"] = AgentLLMClient._to_text(normalised.get("tone_summary")) or ""
        normalised["suggested_reply"] = AgentLLMClient._to_text(normalised.get("suggested_reply"))
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
    def _build_tone_prompt(message: str, context: Dict[str, Any]) -> str:
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
        parts.append(
            "Return JSON with sentiment (positive/neutral/negative/mixed), confidence (0-1), short tone_summary, strengths[], coaching_tips[], emotional_drivers[], optional suggested_reply, warnings[] (omit when empty). Keep each string under 160 characters."
        )

        return "\n\n".join(parts)

    @staticmethod
    def _build_coaching_prompt(context: Dict[str, Any]) -> str:
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

        parts.append(
            "Each card requires: type keyword (message_draft/daily_question/calendar/custom), short title, summary (<=200 chars), optional confidence (0-1), optional call_to_action, optional suggested_message (<=200 chars)."
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
