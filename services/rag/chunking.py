from __future__ import annotations

import json
import logging
from typing import Any, Optional

from .models import ChunkRecord


class ChunkingHelper:
    """Parse model output into chunk records and provide deterministic fallbacks."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def parse_response(self, response_text: str) -> list[dict[str, Any]]:
        if not response_text:
            return []

        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"Ollama response was not valid JSON: {cleaned}")
            self.logger.info("Ollama response was not valid JSON: %s", cleaned)
            self.logger.debug("Ollama response was not JSON: %s", response_text)
            return []

        if isinstance(parsed, list):
            chunks: list[dict[str, Any]] = []
            for item in parsed:
                if isinstance(item, dict) and isinstance(item.get("chunk_text"), str):
                    chunk_text = item["chunk_text"].strip()
                    if chunk_text:
                        chunks.append(
                            {
                                "chunk": chunk_text,
                                "word_count": int(item.get("word_count") or len(chunk_text.split())),
                                "headline": str(item.get("headline", "")).strip(),
                                "summary": str(item.get("summary", "")).strip(),
                                "metadata_facts": {fact.get("key"): fact.get("value") for fact in item.get("metadata_facts", []) if isinstance(fact, dict) and "key" in fact and "value" in fact},
                            }
                        )
            return chunks

        if isinstance(parsed, dict) and isinstance(parsed.get("chunks"), list):
            chunks = []
            for item in parsed["chunks"]:
                if isinstance(item, dict) and isinstance(item.get("chunk_text"), str):
                    chunk_text = item["chunk_text"].strip()
                    if chunk_text:
                        chunks.append(
                            {
                                "chunk": chunk_text,
                                "word_count": int(item.get("word_count") or len(chunk_text.split())),
                                "headline": str(item.get("headline", "")).strip(),
                                "summary": str(item.get("summary", "")).strip(),
                                "metadata_facts": {fact.get("key"): fact.get("value") for fact in item.get("metadata_facts", []) if isinstance(fact, dict) and "key" in fact and "value" in fact},
                            }
                        )
            return chunks

        return []

    def fallback_chunk_text(self, document_name: str, text: str) -> list[ChunkRecord]:
        words = text.split()
        if not words:
            return []

        target_words = 100
        overlap_words = 20
        step = target_words - overlap_words
        chunks: list[ChunkRecord] = []

        for index, start in enumerate(range(0, len(words), step)):
            end = min(start + target_words, len(words))
            chunk_words = words[start:end]
            if not chunk_words:
                continue
            if index > 0 and len(chunk_words) < 20:
                break
            chunks.append(
                ChunkRecord(
                    document_name=document_name,
                    chunk_index=index,
                    chunk_text=" ".join(chunk_words),
                    word_count=len(chunk_words),
                    headline=f"Chunk {index + 1}",
                    summary="Auto-generated chunk from the source document.",
                    metadata_facts=[],
                )
            )

        if not chunks:
            chunks.append(
                ChunkRecord(
                    document_name=document_name,
                    chunk_index=0,
                    chunk_text=text,
                    word_count=len(words),
                    headline="Document Overview",
                    summary="Auto-generated overview chunk for the source document.",
                    metadata_facts=[],
                )
            )

        return chunks


__all__ = ["ChunkingHelper"]
