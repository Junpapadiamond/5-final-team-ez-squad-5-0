from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence

from bson import ObjectId

from .. import mongo
from ..config import Config
from ..utils.cache import RedisCache
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class RetrievalService:
    """Central access point for RAG lookups and caching."""

    _VECTOR_BACKEND = os.getenv("RAG_VECTOR_BACKEND", Config.RAG_VECTOR_BACKEND).lower()
    _ATLAS_INDEX = os.getenv("RAG_ATLAS_INDEX", "agent_embeddings_index")
    _TOP_K = Config.RAG_TOP_K

    @classmethod
    def is_enabled(cls) -> bool:
        flag = os.getenv("RAG_FEATURE_FLAG", Config.RAG_FEATURE_FLAG)
        return flag.lower() in {"1", "true", "yes"}

    @classmethod
    def _collection(cls):
        return mongo.db[Config.RAG_EMBEDDING_COLLECTION]

    @staticmethod
    def _playbook_collection():
        return mongo.db[Config.RAG_PLAYBOOK_COLLECTION]

    @classmethod
    def fetch_context(
        cls,
        *,
        user_id: Optional[str],
        intents: Sequence[str],
        query_text: Optional[str] = None,
        limit: Optional[int] = None,
        include_playbooks: bool = True,
    ) -> List[Dict[str, Any]]:
        if not cls.is_enabled():
            return []

        intents_tuple = tuple(sorted(set(filter(None, intents or []))))
        cache_key = cls._cache_key(user_id, intents_tuple, query_text)
        cached = RedisCache.get(cache_key)
        if cached:
            return cached

        query_embedding: Optional[List[float]] = None
        if query_text:
            query_embedding = cls._embed_text(query_text)

        if not query_embedding and not intents_tuple:
            logger.debug("No query/intents provided for retrieval; returning empty set.")
            return []

        collection = cls._collection()
        top_k = limit or cls._TOP_K
        documents: List[Dict[str, Any]] = []

        if query_embedding and cls._VECTOR_BACKEND in {"atlas", "mongo"}:
            documents = cls._query_atlas(collection, query_embedding, intents_tuple, top_k)

        if not documents:
            documents = cls._query_fallback(collection, query_embedding, intents_tuple, top_k)

        if include_playbooks:
            documents.extend(cls._load_playbook_snippets(intents_tuple, max(1, top_k // 2)))

        formatted = cls._format_results(documents, top_k)
        if formatted:
            RedisCache.set(cache_key, formatted, Config.RAG_REDIS_TTL_SECONDS)
        return formatted

    @classmethod
    def _query_atlas(
        cls,
        collection,
        query_embedding: List[float],
        intents: Sequence[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": cls._ATLAS_INDEX,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(top_k * 10, 50),
                    "limit": top_k * 2,
                    "filter": {"intents": {"$in": list(intents)}} if intents else None,
                }
            },
            {
                "$project": {
                    "content": 1,
                    "source_path": 1,
                    "section": 1,
                    "intents": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        # Remove None filters to avoid Atlas errors
        if pipeline[0]["$vectorSearch"]["filter"] is None:
            del pipeline[0]["$vectorSearch"]["filter"]
        try:
            return list(collection.aggregate(pipeline))
        except Exception as exc:  # pragma: no cover - depends on backend
            logger.warning("Atlas vector search failed, falling back to manual ranking: %s", exc)
            return []

    @classmethod
    def _query_fallback(
        cls,
        collection,
        query_embedding: Optional[List[float]],
        intents: Sequence[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        filter_query: Dict[str, Any] = {}
        if intents:
            filter_query["intents"] = {"$in": list(intents)}
        cursor = collection.find(filter_query).limit(max(top_k * 5, 50))
        docs = list(cursor)
        if not query_embedding:
            return docs[:top_k]

        scored: List[Dict[str, Any]] = []
        for doc in docs:
            embedding = doc.get("embedding")
            if not isinstance(embedding, list):
                continue
            score = cls._cosine_similarity(query_embedding, embedding)
            doc["score"] = score
            scored.append(doc)

        scored.sort(key=lambda item: item.get("score", 0), reverse=True)
        return scored[:top_k]

    @classmethod
    def _load_playbook_snippets(cls, intents: Sequence[str], limit: int) -> List[Dict[str, Any]]:
        try:
            query: Dict[str, Any] = {}
            if intents:
                query["intents"] = {"$in": list(intents)}
            playbooks = list(
                cls._playbook_collection()
                .find(query)
                .sort("priority", -1)
                .limit(limit)
            )
            for doc in playbooks:
                doc["score"] = doc.get("priority", 0.5)
                doc.setdefault("source_path", "agent_playbooks")
                doc.setdefault("section", doc.get("title"))
                doc.setdefault("content", doc.get("summary", ""))
                doc.setdefault("metadata", {})
            return playbooks
        except Exception as exc:  # pragma: no cover - optional collection
            logger.debug("Failed to load playbook snippets: %s", exc)
            return []

    @classmethod
    def _format_results(cls, documents: Iterable[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for index, doc in enumerate(documents):
            if index >= limit:
                break
            content = (doc.get("content") or "").strip()
            if not content:
                continue
            chunk_id = doc.get("_id")
            if isinstance(chunk_id, ObjectId):
                chunk_id = str(chunk_id)
            citation = cls._build_citation(doc)
            formatted.append(
                {
                    "chunk_id": chunk_id,
                    "content": content,
                    "citation": citation,
                    "intents": doc.get("intents") or [],
                    "metadata": doc.get("metadata") or {},
                    "score": float(doc.get("score", 0)),
                    "prompt_snippet": f"{content}\n{citation}",
                }
            )
        return formatted

    @staticmethod
    def _build_citation(doc: Dict[str, Any]) -> str:
        source_path = doc.get("source_path") or "unknown"
        section = doc.get("section") or "General"
        return f"[Source: {source_path} §{section}]"

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @classmethod
    def _embed_text(cls, text: str) -> Optional[List[float]]:
        if not text:
            return None
        embedding = OpenAIClient.embed_text(text)
        if not embedding:
            logger.warning("Failed to generate embedding for retrieval query.")
        return embedding

    @staticmethod
    def _cache_key(user_id: Optional[str], intents: Sequence[str], query_text: Optional[str]) -> str:
        key_material = {
            "user": user_id or "anon",
            "intents": list(intents),
            "query_hash": hashlib.sha1((query_text or "").encode("utf-8")).hexdigest(),
        }
        return f"rag:{key_material['user']}:{','.join(key_material['intents'])}:{key_material['query_hash']}"


__all__ = ["RetrievalService"]
