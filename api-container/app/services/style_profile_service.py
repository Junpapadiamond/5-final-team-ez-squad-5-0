from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .. import mongo


class StyleProfileService:
    """Builds lightweight linguistic fingerprints for a user's messages."""

    _EMOJI_PATTERN = re.compile(
        "[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]+"
    )
    _WORD_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)
    _STOPWORDS = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "have",
        "this",
        "from",
        "your",
        "about",
        "their",
        "just",
        "will",
        "would",
        "could",
        "should",
        "them",
        "when",
        "what",
        "where",
        "why",
        "how",
        "you",
        "you're",
        "im",
        "i'm",
    }

    @staticmethod
    def get_style_profile(
        user_id: str,
        *,
        force_refresh: bool = False,
        cache_ttl_hours: int = 24,
        sample_limit: int = 200,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Return a cached or freshly computed style profile."""
        now = datetime.utcnow()

        existing = mongo.db.style_profiles.find_one({"user_id": user_id})
        if (
            existing
            and not force_refresh
            and (existing.get("updated_at") and existing["updated_at"] >= now - timedelta(hours=cache_ttl_hours))
        ):
            profile = StyleProfileService._format_profile(existing)
            profile["cached"] = True
            return profile, None

        messages = StyleProfileService._fetch_messages(user_id, sample_limit)
        if not messages:
            return {
                "user_id": user_id,
                "message_count": 0,
                "style_summary": "Not enough messages to build a profile yet.",
                "signature_examples": [],
                "updated_at": now.isoformat() + "Z",
                "cached": False,
            }, None

        profile_body = StyleProfileService._build_profile(messages)
        profile_doc = {
            "user_id": user_id,
            "data": profile_body,
            "message_count": profile_body["message_count"],
            "updated_at": now,
        }

        mongo.db.style_profiles.update_one(
            {"user_id": user_id},
            {"$set": profile_doc},
            upsert=True,
        )

        profile = StyleProfileService._format_profile(profile_doc)
        profile["cached"] = False
        return profile, None

    @staticmethod
    def register_sample(user_id: str, content: str) -> None:
        if not content or not content.strip():
            return

        collection = getattr(mongo.db, "style_samples", None)
        if collection is None:
            return

        sample_doc = {
            "user_id": user_id,
            "content": content.strip(),
            "created_at": datetime.utcnow(),
        }

        collection.insert_one(sample_doc)

        overflow_cursor = collection.find({"user_id": user_id}).sort("created_at", -1).skip(300)
        overflow_ids = [doc["_id"] for doc in overflow_cursor]
        if overflow_ids:
            collection.delete_many({"_id": {"$in": overflow_ids}})

    @staticmethod
    def _fetch_messages(user_id: str, limit: int) -> List[Dict[str, Any]]:
        messages_cursor = mongo.db.messages.find({"sender_id": user_id}).sort("created_at", -1).limit(limit)
        messages = [doc for doc in messages_cursor if doc.get("content")]

        samples = []
        collection = getattr(mongo.db, "style_samples", None)
        if collection is not None:
            samples_cursor = collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            samples = [
                {
                    "_id": doc.get("_id"),
                    "sender_id": user_id,
                    "content": doc.get("content"),
                    "created_at": doc.get("created_at"),
                }
                for doc in samples_cursor
                if doc.get("content")
            ]

        combined = messages + samples
        combined.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=True,
        )

        return combined[:limit]

    @staticmethod
    def _build_profile(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_chars = 0
        total_words = 0
        emoji_counter: Counter[str] = Counter()
        punctuation_counter: Counter[str] = Counter()
        word_counter: Counter[str] = Counter()

        signature_examples: List[str] = []

        for message in messages:
            content = str(message.get("content", "")).strip()
            if not content:
                continue

            total_chars += len(content)

            words = StyleProfileService._WORD_PATTERN.findall(content.lower())
            filtered_words = [w for w in words if w not in StyleProfileService._STOPWORDS]
            word_counter.update(filtered_words)
            total_words += len(words)

            emojis = StyleProfileService._EMOJI_PATTERN.findall(content)
            if emojis:
                emoji_counter.update(emojis)

            punctuation_counter.update(ch for ch in content if ch in {"!", "?", "~"})
            if "..." in content:
                punctuation_counter["..."] += content.count("...")

            if len(signature_examples) < 3:
                signature_examples.append(content)

        message_count = len(messages)
        average_length = total_chars / message_count if message_count else 0
        average_words = total_words / message_count if message_count else 0

        emoji_total = sum(emoji_counter.values())
        emoji_density = emoji_total / total_words if total_words else 0

        top_emojis = [{"emoji": emoji, "count": count} for emoji, count in emoji_counter.most_common(5)]
        top_words = [{"word": word, "count": count} for word, count in word_counter.most_common(10)]

        style_summary = StyleProfileService._build_summary(
            average_length=average_length,
            average_words=average_words,
            emoji_density=emoji_density,
            top_emojis=top_emojis,
            punctuation=punctuation_counter,
        )

        return {
            "message_count": message_count,
            "average_length": round(average_length, 2),
            "average_words": round(average_words, 2),
            "emoji_density": round(emoji_density, 3),
            "emoji_frequency": top_emojis,
            "punctuation_usage": dict(punctuation_counter),
            "top_words": top_words,
            "signature_examples": signature_examples,
            "style_summary": style_summary,
        }

    @staticmethod
    def _build_summary(
        *,
        average_length: float,
        average_words: float,
        emoji_density: float,
        top_emojis: List[Dict[str, Any]],
        punctuation: Counter[str],
    ) -> str:
        summary_bits: List[str] = []

        if emoji_density >= 0.05 and top_emojis:
            summary_bits.append(
                f"Loves using emojis (favorites: {', '.join(item['emoji'] for item in top_emojis[:3])})."
            )
        elif emoji_density < 0.01:
            summary_bits.append("Rarely uses emojis, tends to keep messages straightforward.")

        punctuation_total = sum(punctuation.values()) or 1

        exclaim_ratio = punctuation.get("!", 0) / punctuation_total
        question_ratio = punctuation.get("?", 0) / punctuation_total

        if exclaim_ratio > 0.2:
            summary_bits.append("Often uses exclamation marks for enthusiastic tone.")

        if question_ratio > 0.2:
            summary_bits.append("Frequently asks questions, suggesting an engaging conversational style.")

        if average_words >= 18:
            summary_bits.append("Writes longer, descriptive messages.")
        elif average_words <= 6:
            summary_bits.append("Prefers short and snappy messages.")

        if not summary_bits:
            summary_bits.append("Balanced tone with varied phrasing.")

        return " ".join(summary_bits)

    @staticmethod
    def _format_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(doc.get("data", {}))
        data.update(
            {
                "user_id": doc.get("user_id"),
                "message_count": doc.get("message_count", data.get("message_count", 0)),
                "updated_at": StyleProfileService._format_timestamp(doc.get("updated_at")),
            }
        )
        return data

    @staticmethod
    def _format_timestamp(value: Any) -> Optional[str]:
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return value
