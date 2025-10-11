from __future__ import annotations

import logging
import os
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class OpenAIClient:
    _client: Optional["OpenAI"] = None

    @classmethod
    def _is_configured(cls) -> bool:
        return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None

    @classmethod
    def _get_client(cls) -> Optional["OpenAI"]:
        if not cls._is_configured():
            return None

        if cls._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            cls._client = OpenAI(api_key=api_key)
        return cls._client

    @classmethod
    def summarize_tone(cls, text: str) -> Optional[str]:
        client = cls._get_client()
        if client is None:
            return None

        try:
            prompt = (
                "You are a relationship communication coach. "
                "Given the following message, briefly summarize the emotional tone "
                "and suggest how to respond empathetically in 2 sentences.\n\n"
                f"Message: {text}"
            )

            response = client.responses.create(
                model=os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"),
                input=prompt,
                max_output_tokens=120,
            )

            if response and response.output and len(response.output) > 0:
                first_item = response.output[0]
                content = getattr(first_item, "content", None)
                if content and len(content) > 0:
                    return content[0].text

            logger.warning("OpenAI response did not contain expected content")
            return None
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("OpenAI summarize_tone failed: %s", exc)
            return None
