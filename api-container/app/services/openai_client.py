from __future__ import annotations

import logging
import os
from typing import List, Optional, Sequence

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
    def is_available(cls) -> bool:
        return cls._is_configured()

    @classmethod
    def get_client(cls) -> Optional["OpenAI"]:
        return cls._get_client()

    @classmethod
    def _get_client(cls) -> Optional["OpenAI"]:
        if not cls._is_configured():
            return None

        if cls._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            try:
                cls._client = OpenAI(api_key=api_key)
            except TypeError as exc:
                httpx_version = cls._get_httpx_version()
                logger.warning(
                    "OpenAI client initialization failed due to incompatible httpx%s: %s",
                    f" (installed={httpx_version})" if httpx_version else "",
                    exc,
                )
                cls._client = None
                return None
            except Exception as exc:  # pragma: no cover - unexpected init failure
                logger.warning("OpenAI client initialization failed: %s", exc)
                cls._client = None
                return None
        return cls._client

    @staticmethod
    def _get_httpx_version() -> Optional[str]:
        try:  # pragma: no cover - diagnostic helper
            import httpx

            return getattr(httpx, "__version__", None)
        except Exception:
            return None

    @classmethod
    def summarize_tone(cls, text: str) -> Optional[str]:
        client = cls._get_client()
        if client is None:
            return None

        prompt = (
            "You are a relationship communication coach. "
            "Given the following message, briefly summarize the emotional tone "
            "and suggest how to respond empathetically in 2 sentences.\n\n"
            f"Message: {text}"
        )

        if hasattr(client, "responses"):
            try:
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

        return cls._fallback_chat_completion(prompt)

    @staticmethod
    def _fallback_chat_completion(prompt: str) -> Optional[str]:
        client = OpenAIClient.get_client()
        if client is None or not hasattr(client, "chat"):
            return None

        try:
            completion = client.chat.completions.create(
                model=os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a relationship communication coach. "
                            "Keep responses under 2 sentences."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=120,
            )

            message = completion.choices[0].message
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list) and content:
                return content[0].get("text")
            return None
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("OpenAI chat completion fallback failed: %s", exc)
            return None

    @classmethod
    def embed_text(cls, text: str) -> Optional[List[float]]:
        embeddings = cls.embed_texts([text])
        return embeddings[0] if embeddings else None

    @classmethod
    def embed_texts(cls, texts: Sequence[str]) -> List[List[float]]:
        client = cls._get_client()
        if client is None:
            return []
        if not texts:
            return []
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        try:
            response = client.embeddings.create(
                model=model,
                input=list(texts),
            )
            vectors: List[List[float]] = []
            for item in getattr(response, "data", []):
                embedding = getattr(item, "embedding", None)
                if embedding:
                    vectors.append(list(embedding))
            return vectors
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("OpenAI embedding request failed: %s", exc)
            return []
