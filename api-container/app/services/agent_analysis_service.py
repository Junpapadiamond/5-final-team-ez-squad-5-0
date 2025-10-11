from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .. import mongo
from ..ml.sentiment_model import SentimentModel
from .agent_orchestrator import AgentOrchestrator
from .openai_client import OpenAIClient
from .style_profile_service import StyleProfileService


class AgentAnalysisService:
    """Produces conversational analysis for user drafts with LLM-backed insights and deterministic fallbacks."""

    EMOJI_PATTERN = re.compile(
        "[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]+"
    )
    WORD_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)

    @staticmethod
    def analyze_input(user_id: str, content: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not content or not content.strip():
            return None, "Content is required"

        text = content.strip()
        metrics = AgentAnalysisService._compute_baseline_metrics(text)
        StyleProfileService.register_sample(user_id, text)
        profile, _ = StyleProfileService.get_style_profile(user_id, force_refresh=False)

        cache_payload = AgentAnalysisService._get_cached_analysis(user_id, text)
        if cache_payload:
            cache_payload["style_profile"] = profile
            cache_payload["cached"] = True
            return cache_payload, None

        llm_payload = AgentOrchestrator.analyze_tone(user_id, text)
        if llm_payload:
            result = AgentAnalysisService._build_llm_response(metrics, profile, llm_payload)
            AgentAnalysisService._store_cache(user_id, text, result)
            return result, None

        legacy_result = AgentAnalysisService._legacy_analysis(metrics, profile, text)
        AgentAnalysisService._store_cache(user_id, text, legacy_result)
        return legacy_result, None

    @staticmethod
    def _compute_baseline_metrics(text: str) -> Dict[str, Any]:
        words = AgentAnalysisService.WORD_PATTERN.findall(text.lower())
        word_count = len(words)
        char_count = len(text)
        emojis = AgentAnalysisService.EMOJI_PATTERN.findall(text)
        emoji_count = len(emojis)
        punctuation_counter = Counter(ch for ch in text if ch in {"!", "?", ".", ","})

        keyword_candidates = [w for w in words if len(w) > 3]
        keyword_counts = Counter(keyword_candidates)
        keywords = [word for word, _ in keyword_counts.most_common(6)]

        return {
            "text": text,
            "words": words,
            "length": {
                "characters": char_count,
                "words": word_count,
            },
            "emoji_count": emoji_count,
            "punctuation": punctuation_counter,
            "keywords": keywords,
        }

    @staticmethod
    def _build_llm_response(
        metrics: Dict[str, Any],
        profile: Optional[Dict[str, Any]],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        analysis = {
            "length": metrics["length"],
            "emoji_count": metrics["emoji_count"],
            "punctuation": dict(metrics["punctuation"]),
            "sentiment": payload.get("sentiment", "neutral"),
            "sentiment_probability_positive": payload.get("confidence", 0),
            "keywords": metrics["keywords"],
            "emotional_drivers": payload.get("emotional_drivers", []),
        }

        result = {
            "analysis": analysis,
            "strengths": payload.get("strengths", []),
            "tips": payload.get("coaching_tips", []),
            "style_profile": profile,
            "llm_feedback": payload.get("tone_summary"),
            "suggested_reply": payload.get("suggested_reply"),
            "warnings": payload.get("warnings", []),
            "ai_source": "openai",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        return result

    @staticmethod
    def _legacy_analysis(
        metrics: Dict[str, Any],
        profile: Optional[Dict[str, Any]],
        text: str,
    ) -> Dict[str, Any]:
        sentiment_result = SentimentModel.predict(text)
        sentiment = sentiment_result.label

        analysis = {
            "length": metrics["length"],
            "emoji_count": metrics["emoji_count"],
            "punctuation": dict(metrics["punctuation"]),
            "sentiment": sentiment,
            "sentiment_probability_positive": sentiment_result.probability_positive,
            "keywords": metrics["keywords"],
        }

        tips = AgentAnalysisService._generate_legacy_tips(
            word_count=metrics["length"]["words"],
            emoji_count=metrics["emoji_count"],
            punctuation=metrics["punctuation"],
            sentiment=sentiment,
        )
        strengths = AgentAnalysisService._identify_legacy_strengths(
            word_count=metrics["length"]["words"],
            emoji_count=metrics["emoji_count"],
            sentiment=sentiment,
        )

        llm_feedback = None
        if OpenAIClient.is_available():
            llm_feedback = OpenAIClient.summarize_tone(text)

        return {
            "analysis": analysis,
            "strengths": strengths,
            "tips": tips,
            "style_profile": profile,
            "llm_feedback": llm_feedback,
            "ai_source": "legacy",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def _generate_legacy_tips(
        *,
        word_count: int,
        emoji_count: int,
        punctuation: Counter,
        sentiment: str,
    ) -> List[str]:
        tips: List[str] = []

        if word_count < 4:
            tips.append("Consider adding a bit more detail so your partner has something to respond to.")
        elif word_count > 60:
            tips.append("It’s a long message—maybe break it into shorter notes or plan a call.")

        if emoji_count == 0:
            tips.append("Add an emoji to bring warmth (e.g. 😊 or ❤️).")
        elif emoji_count > 5:
            tips.append("Maybe trim a few emojis so the message stays clear.")

        if punctuation.get("!") and punctuation["!"] > 3:
            tips.append("Lots of exclamation marks—double-check your tone if you want a mellow vibe.")

        if sentiment == "negative":
            tips.append("Since the tone feels tense, acknowledge feelings gently and invite dialogue.")
        elif sentiment == "neutral":
            tips.append("Add a personal note or appreciation to keep things heartfelt.")

        if not tips:
            tips.append("Looks great—send it with confidence!")

        return tips

    @staticmethod
    def _identify_legacy_strengths(
        *,
        word_count: int,
        emoji_count: int,
        sentiment: str,
    ) -> List[str]:
        strengths: List[str] = []
        if 6 <= word_count <= 50:
            strengths.append("Nice balance of detail and brevity.")
        if emoji_count > 0:
            strengths.append("Friendly feel with emojis.")
        if sentiment == "positive":
            strengths.append("Positive tone that lifts the conversation.")
        return strengths

    @staticmethod
    def _cache_ttl_hours() -> int:
        try:
            return max(0, int(os.getenv("AGENT_TONE_CACHE_HOURS", "3")))
        except ValueError:
            return 0

    @staticmethod
    def _cache_collection():
        return getattr(mongo.db, "agent_tone_cache", None)

    @staticmethod
    def _cache_key(user_id: str, text: str) -> str:
        return hashlib.sha256(f"{user_id}:{text}".encode("utf-8")).hexdigest()

    @staticmethod
    def _get_cached_analysis(user_id: str, text: str) -> Optional[Dict[str, Any]]:
        collection = AgentAnalysisService._cache_collection()
        ttl_hours = AgentAnalysisService._cache_ttl_hours()
        if collection is None or ttl_hours <= 0:
            return None

        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        key = AgentAnalysisService._cache_key(user_id, text)

        doc = collection.find_one({"user_id": user_id, "hash": key, "created_at": {"$gte": cutoff}})
        if doc:
            payload = doc.get("payload")
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _store_cache(user_id: str, text: str, payload: Dict[str, Any]) -> None:
        collection = AgentAnalysisService._cache_collection()
        if collection is None:
            return
        key = AgentAnalysisService._cache_key(user_id, text)
        collection.update_one(
            {"user_id": user_id, "hash": key},
            {"$set": {"payload": payload, "created_at": datetime.utcnow()}},
            upsert=True,
        )
