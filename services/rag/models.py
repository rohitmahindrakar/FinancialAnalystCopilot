from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from weakref import WeakKeyDictionary


_EMBEDDING_CACHE: WeakKeyDictionary[object, Optional[list[float]]] = WeakKeyDictionary()


@dataclass(slots=True)
class ChunkRecord:
    """Represents a single chunk produced for a document."""

    document_name: str
    chunk_index: int
    chunk_text: str = field(
        default="",
        metadata={"description": "The original text of this chunk from the provided document, exactly as is, not changed in any way"},
    )
    word_count: int = 0
    headline: str = field(
        default="",
        metadata={"description": "A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query"},
    )
    summary: str = field(
        default="",
        metadata={"description": "A few sentences summarizing the content of this chunk to answer common questions"},
    )
    embedding: Optional[list[float]] = field(default=None, repr=False)

    def __getattribute__(self, name: str) -> Any:
        if name == "embedding":
            fields = getattr(type(self), "__dataclass_fields__", {})
            if "embedding" in fields:
                return object.__getattribute__(self, name)
            return _EMBEDDING_CACHE.get(self)
        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "embedding":
            fields = getattr(type(self), "__dataclass_fields__", {})
            if "embedding" in fields:
                object.__setattr__(self, name, value)
            else:
                _EMBEDDING_CACHE[self] = value
            return
        object.__setattr__(self, name, value)


@dataclass(slots=True)
class IngestionResult:
    """Represents the ingestion outcome for one document."""

    document_name: str
    source_path: str
    text_length: int
    chunk_count: int
    chunks: list[ChunkRecord]


__all__ = ["ChunkRecord", "IngestionResult"]
