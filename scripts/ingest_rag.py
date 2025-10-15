#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

# Ensure api-container is importable
ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "api-container"
sys.path.append(str(API_PATH))

from app import create_app, mongo  # type: ignore  # noqa: E402
from app.config import Config  # type: ignore  # noqa: E402
from app.services.openai_client import OpenAIClient  # type: ignore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_rag")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WHITESPACE_PATTERN = re.compile(r"\s+")


def load_docs(directory: Path) -> List[Tuple[Path, str]]:
    documents: List[Tuple[Path, str]] = []
    for path in directory.rglob("*.md"):
        if path.name.startswith("."):
            continue
        try:
            documents.append((path, path.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning("Failed to read %s: %s", path, exc)
    return documents


def chunk_markdown(path: Path, content: str, chunk_size_tokens: int = 400) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []
    current_title = "Introduction"
    buffer: List[str] = []

    for line in content.splitlines():
        if line.strip().startswith("#"):
            # Flush buffer
            flush_section(sections, current_title, buffer, chunk_size_tokens)
            buffer = []
            current_title = WHITESPACE_PATTERN.sub(" ", line.strip("# ").strip()) or current_title
        else:
            buffer.append(line)

    flush_section(sections, current_title, buffer, chunk_size_tokens)
    for section in sections:
        section["source_path"] = str(path.relative_to(ROOT))
    return sections


def flush_section(
    sections: List[Dict[str, str]],
    title: str,
    lines: Sequence[str],
    chunk_size_tokens: int,
) -> None:
    if not lines:
        return
    text = "\n".join(lines).strip()
    if not text:
        return
    paragraphs = [para.strip() for para in text.split("\n\n") if para.strip()]
    chunk: List[str] = []
    token_count = 0
    for para in paragraphs:
        para_tokens = len(para.split())
        if token_count + para_tokens > chunk_size_tokens and chunk:
            sections.append(
                {
                    "section": title,
                    "content": sanitize_text("\n\n".join(chunk)),
                }
            )
            chunk = [para]
            token_count = para_tokens
        else:
            chunk.append(para)
            token_count += para_tokens
    if chunk:
        sections.append(
            {
                "section": title,
                "content": sanitize_text("\n\n".join(chunk)),
            }
        )


def sanitize_text(text: str) -> str:
    cleaned = EMAIL_PATTERN.sub("<email>", text)
    cleaned = cleaned.replace("\r", " ").strip()
    return cleaned


def infer_intents(path: Path, section: str) -> List[str]:
    intents: List[str] = []
    haystack = f"{path.as_posix()} {section}".lower()
    if any(keyword in haystack for keyword in ("daily", "reflection", "question")):
        intents.append("daily_check_in")
    if any(keyword in haystack for keyword in ("message", "tone", "reply")):
        intents.append("tone_analysis")
        intents.append("coaching")
    if any(keyword in haystack for keyword in ("calendar", "event", "plan", "schedule")):
        intents.append("calendar")
    if any(keyword in haystack for keyword in ("quiz", "session", "score")):
        intents.append("quiz_follow_up")
    if not intents:
        intents.append("general")
    return intents


def embed_chunks(chunks: List[Dict[str, str]], batch_size: int = 64) -> None:
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embeddings = OpenAIClient.embed_texts([chunk["content"] for chunk in batch])
        if not embeddings:
            raise RuntimeError("Embedding request returned no vectors.")
        for chunk, vector in zip(batch, embeddings):
            chunk["embedding"] = vector


def upsert_chunks(
    chunks: Iterable[Dict[str, str]],
    *,
    version: str,
    intents_hint: Dict[str, List[str]],
    prune_other_versions: bool,
) -> None:
    collection = mongo.db[Config.RAG_EMBEDDING_COLLECTION]
    upserted = 0
    for chunk in chunks:
        content_hash = hashlib.sha1(chunk["content"].encode("utf-8")).hexdigest()
        intents = intents_hint.get(chunk["source_path"], []) or infer_intents(Path(chunk["source_path"]), chunk["section"])
        document = {
            "content": chunk["content"],
            "source_path": chunk["source_path"],
            "section": chunk["section"],
            "intents": intents,
            "embedding": chunk.get("embedding"),
            "metadata": {
                "ingested_at": datetime.utcnow().isoformat() + "Z",
                "embedding_version": version,
            },
            "embedding_version": version,
        }
        collection.update_one(
            {"_id": content_hash},
            {"$set": document},
            upsert=True,
        )
        upserted += 1
    logger.info("Upserted %s embedding chunks.", upserted)

    if prune_other_versions:
        deleted = collection.delete_many({"embedding_version": {"$ne": version}}).deleted_count
        if deleted:
            logger.info("Pruned %s stale embedding chunks.", deleted)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Together docs into the RAG embeddings collection.")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=ROOT / "docs",
        help="Directory containing markdown sources (default: ./docs)",
    )
    parser.add_argument(
        "--version",
        default=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        help="Embedding version label stored on each chunk.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete chunks from previous embedding versions after ingest.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not RetrievalFeatureGuard.is_enabled():
        logger.error("RAG feature flag disabled. Set RAG_FEATURE_FLAG=1 to ingest.")
        sys.exit(1)

    docs = load_docs(args.docs_dir)
    if not docs:
        logger.warning("No markdown files found in %s", args.docs_dir)
        return

    chunks: List[Dict[str, str]] = []
    intents_hint: Dict[str, List[str]] = {}
    for path, text in docs:
        for chunk in chunk_markdown(path, text):
            if not chunk.get("content"):
                continue
            rel_path = chunk["source_path"]
            chunk_id = f"{rel_path}::{chunk['section']}"
            chunk["chunk_id"] = chunk_id
            chunks.append(chunk)
            intents_hint.setdefault(rel_path, infer_intents(path, chunk["section"]))

    logger.info("Prepared %s content chunks. Generating embeddings...", len(chunks))
    embed_chunks(chunks, batch_size=64)

    upsert_chunks(
        chunks,
        version=args.version,
        intents_hint=intents_hint,
        prune_other_versions=args.prune,
    )
    logger.info("Ingestion complete. Version=%s", args.version)


class RetrievalFeatureGuard:
    @staticmethod
    def is_enabled() -> bool:
        flag = os.getenv("RAG_FEATURE_FLAG", Config.RAG_FEATURE_FLAG)
        return flag.lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    app = create_app(os.getenv("FLASK_CONFIG", "default"))
    with app.app_context():
        main()
