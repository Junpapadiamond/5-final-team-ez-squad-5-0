from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .style_profile_service import StyleProfileService
from ..ml.sentiment_model import SentimentModel
from .openai_client import OpenAIClient


class AgentAnalysisService:
    POSITIVE_WORDS = {
        "love",
        "happy",
        "great",
        "excited",
        "grateful",
        "proud",
        "appreciate",
        "wonderful",
        "amazing",
    }
    NEGATIVE_WORDS = {
        "sad",
        "angry",
        "upset",
        "tired",
        "frustrated",
        "worried",
        "anxious",
        "depressed",
    }

    @staticmethod
    def analyze_input(user_id: str, content: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not content or not content.strip():
            return None, "Content is required"

        text = content.strip()
        words = re.findall(r"\b[\w']+\b", text.lower())
        word_count = len(words)
        char_count = len(text)

        emoji_matches = re.findall(
            "[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]+",
            text,
        )
        emoji_count = len(emoji_matches)

        punctuation_counter = Counter(ch for ch in text if ch in {"!", "?", ".", ","})

        sentiment_result = SentimentModel.predict(text)
        sentiment = sentiment_result.label

        positive_hits = [w for w in words if w in AgentAnalysisService.POSITIVE_WORDS]
        negative_hits = [w for w in words if w in AgentAnalysisService.NEGATIVE_WORDS]

        if sentiment == "neutral":
            if positive_hits and not negative_hits:
                sentiment = "positive"
            elif negative_hits and not positive_hits:
                sentiment = "negative"

        tips = AgentAnalysisService._generate_tips(
            word_count=word_count,
            emoji_count=emoji_count,
            punctuation=punctuation_counter,
            sentiment=sentiment,
        )

        strengths = AgentAnalysisService._identify_strengths(
            word_count=word_count,
            emoji_count=emoji_count,
            sentiment=sentiment,
        )

        StyleProfileService.register_sample(user_id, text)
        profile, _ = StyleProfileService.get_style_profile(user_id, force_refresh=True, cache_ttl_hours=0)

        llm_feedback = OpenAIClient.summarize_tone(text)

        analysis = {
            "length": {
                "characters": char_count,
                "words": word_count,
            },
            "emoji_count": emoji_count,
            "punctuation": dict(punctuation_counter),
            "sentiment": sentiment,
            "sentiment_probability_positive": sentiment_result.probability_positive,
            "keywords": list(dict.fromkeys(positive_hits + negative_hits)),
        }

        return {
            "analysis": analysis,
            "strengths": strengths,
            "tips": tips,
            "style_profile": profile,
            "llm_feedback": llm_feedback,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }, None

    @staticmethod
    def _generate_tips(
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
            tips.append("Since the tone feels tense, you could acknowledge feelings gently and invite dialogue.")
        elif sentiment == "neutral":
            tips.append("Add a personal note or appreciation to keep things heartfelt.")

        if not tips:
            tips.append("Looks great—send it with confidence!")

        return tips

    @staticmethod
    def _identify_strengths(
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
