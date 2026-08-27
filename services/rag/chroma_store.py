from __future__ import annotations

from dataclasses import asdict
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

# 'attrs.asdict' was accidentally imported previously, overriding dataclasses.asdict.
# Use dataclasses.asdict for dataclass instances like MetadataFact.
from chromadb import PersistentClient
from chromadb.config import Settings

from .models import ChunkRecord


def _default_chroma_persist_directory(repo_root: Optional[str | Path] = None) -> Path:
    env_path = os.getenv("CHROMA_PERSIST_DIR")
    if env_path:
        env_dir = Path(env_path).expanduser()
        return env_dir if env_dir.is_absolute() else Path(repo_root or Path(__file__).resolve().parents[2]) / env_dir

    root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    return root / "database" / "chroma"


def _default_embedding_function(texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for text in texts:
        tokens = [token.lower() for token in text.replace("\n", " ").split() if token.strip()]
        vector = [0.0] * max(len(tokens), 1)
        for index, token in enumerate(tokens):
            vector[index] = float(len(token))
        embeddings.append(vector)
    return embeddings


class ChunkChromaStore:
    """Tokenize generated chunks and persist them to a local Chroma collection."""

    def __init__(
        self,
        persist_directory: Optional[str | Path] = None,
        collection_name: str = "financial_chunks",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.persist_directory = Path(persist_directory or _default_chroma_persist_directory()).expanduser()
        self.collection_name = collection_name
        self.logger = logger or logging.getLogger(__name__)
        self._client = PersistentClient(path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False))
        self._connect_collection()
        # Chroma can work with arbitrary embedding functions; this lightweight fallback keeps
        # the store usable without downloading a remote model at import time.
        self._collection.add = self._collection.add  # preserve the original method

    def _is_recoverable_chroma_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "nothing found on disk" in message or "segment reader" in message or "hnsw" in message or "collection" in message and "not found" in message

    def _reset_collection(self) -> None:
        self.logger.warning("Chroma collection '%s' is unreadable; recreating it in '%s'", self.collection_name, self.persist_directory)
        try:
            self._client.delete_collection(self.collection_name)
        except Exception as delete_exc:
            self.logger.warning("Unable to delete Chroma collection '%s': %s", self.collection_name, delete_exc)

        try:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as create_exc:
            if self.persist_directory.exists():
                shutil.rmtree(self.persist_directory, ignore_errors=True)
                self.persist_directory.mkdir(parents=True, exist_ok=True)
                self._client = PersistentClient(path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False))
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                raise create_exc

    def _connect_collection(self) -> None:
        try:
            existing_collections = [col.name for col in self._client.list_collections()]
        except Exception as list_exc:
            if self._is_recoverable_chroma_error(list_exc):
                self._reset_collection()
                return
            raise

        try:
            if self.collection_name in existing_collections:
                #delete and recreate the collection to ensure it's in a clean state
                # self._client.delete_collection(self.collection_name)
                # self._collection = self._client.get_or_create_collection(
                #     name=self.collection_name,
                #     metadata={"hnsw:space": "cosine"},
                # )
                self._collection = self._client.get_collection(name=self.collection_name)
            else:
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as connect_exc:
            if self._is_recoverable_chroma_error(connect_exc):
                self._reset_collection()
                return
            raise

    def tokenize_chunk(self, chunk_text: str) -> list[str]:
        return [token.lower() for token in chunk_text.replace("\n", " ").split() if token.strip()]

    def save_chunks(self, chunks: list[ChunkRecord]) -> None:
        if not chunks:
            return

        documents = [chunk.chunk_text for chunk in chunks]
        metadatas: list[dict[str, Any]] = []
        for chunk in chunks:
            md: dict[str, Any] = {
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                "word_count": chunk.word_count,
                "headline": chunk.headline,
                "summary": chunk.summary,
            }
            # Expand metadata facts into top-level keys with primitive values or lists
            for fact in getattr(chunk, "metadata_facts", []) or []:
                key = fact.key
                val = fact.value
                if key in md:
                    # If key already exists, convert to list or append
                    existing = md[key]
                    if isinstance(existing, list):
                        existing.append(val)
                    else:
                        md[key] = [existing, val]
                else:
                    md[key] = val
            metadatas.append(md)
        ids = [f"{chunk.document_name}:{chunk.chunk_index}" for chunk in chunks]

        embeddings = [chunk.embedding for chunk in chunks if getattr(chunk, "embedding", None) is not None]
        try:
            self._collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings or None)
        except Exception as exc:
            if self._is_recoverable_chroma_error(exc):
                self._reset_collection()
                self._collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings or None)
            else:
                raise
        self.logger.info("Saved %d chunks to Chroma collection '%s'", len(chunks), self.collection_name)

    def search(self, query: str, n_results: int = 5) -> dict[str, Any]:
        try:
            return self._collection.query(query_texts=[query], n_results=n_results)
        except Exception as exc:
            if self._is_recoverable_chroma_error(exc):
                self._reset_collection()
                return self._collection.query(query_texts=[query], n_results=n_results)
            raise

    def document_exists(self, document_name: str) -> bool:
        try:
            # Use a metadata filter instead of query_texts so no embedding is generated.
            results = self._collection.get(where={"document_name": document_name}, limit=1, include=[])
            return bool(results.get("ids"))
        except Exception as exc:
            if self._is_recoverable_chroma_error(exc):
                self._reset_collection()
                results = self._collection.get(where={"document_name": document_name}, limit=1, include=[])
                return bool(results.get("ids"))
            raise


__all__ = ["ChunkChromaStore"]
