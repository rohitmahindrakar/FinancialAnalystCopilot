from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from weakref import WeakKeyDictionary
from pydantic import Field

_EMBEDDING_CACHE: WeakKeyDictionary[object, Optional[list[float]]] = WeakKeyDictionary()

@dataclass(slots=True)
class MetadataFact:
    key: str = Field(
        description=(
            "A lowercase snake_case name describing one explicit, "
            "searchable fact from the chunk, such as company_name, business_unit, period, "
            "employee_name, university, department, job_title, location, policy_name, "
            "effective_date, certification, or project_name, etc."
        )
    )

    value: str = Field(
        description=(
            "The exact value of the fact as stated in the source text. "
            "Preserve proper-name capitalization. Do not summarize, "
            "generalize, infer, or invent the value."
        )
    )

@dataclass(slots=True)
class ChunkRecord:
    """Represents a single chunk produced for a document."""

    document_name: str
    chunk_index: int
    chunk_text: str = Field(
        default="",
        metadata={"description": "The original text of this chunk from the provided document, exactly as is, not changed in any way"},
    )
    word_count: int = 0
    headline: str = Field(
        default="",
        metadata={"description": "A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query"},
    )
    summary: str = Field(
        default="",
        metadata={"description": "A few sentences summarizing the content of this chunk to answer common questions"},
    )

    metadata_facts: list[MetadataFact] = Field(
        default_factory=list,
        metadata={
            "description": (
                "All explicit, useful facts in this chunk that may be used "
                "for exact filtering. Extract one item per fact. This list "
                "must not be empty when the chunk contains a person name, "
                "organization, university, department, location, date, "
                "identifier, policy name, certification, project name, "
                "job title, or similar searchable entity. Return an empty "
                "list only when no such explicit facts exist."
            )
        },
    )
    embedding: Optional[list[float]] = Field(default=None, repr=False)

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


__all__ = ["ChunkRecord", "IngestionResult", "MetadataFact"]
