from __future__ import annotations

import logging
import os
from typing import Optional

from pydantic import json
import requests

from .models import ChunkRecord


class OpenAIEmbeddingProvider:
    """Generate embeddings with OpenAI's text-embedding-3-small model."""

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model: str = "text-embedding-3-small") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for embeddings.")

        url = f"{self.api_base.rstrip('/') if self.api_base else 'https://api.openai.com/v1'}/embeddings"
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"input": texts, "model": self.model},
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        return [item["embedding"] for item in payload.get("data", [])]


class LocalSentenceTransformerEmbeddingProvider:
    """Generate embeddings with a local sentence-transformers model."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None) -> None:
        self.model_name = model_name or os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = device or os.getenv("EMBEDDING_DEVICE", "cpu")
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:  # pragma: no cover - defensive path
                raise RuntimeError("sentence-transformers is not installed. Install it to use local embeddings.") from exc
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return embeddings.tolist()


class ChunkEmbedder:
    """Embed chunk text using a configured provider and optionally save vectors to Chroma."""

    def __init__(self, embedding_provider: Optional[object] = None, chroma_store: Optional[object] = None, logger: Optional[logging.Logger] = None) -> None:
        self.embedding_provider = embedding_provider or LocalSentenceTransformerEmbeddingProvider()
        self.chroma_store = chroma_store
        self.logger = logger or logging.getLogger(__name__)

    def _fallback_embedding(self, text: str) -> list[float]:
        tokens = [token.lower() for token in text.replace("\n", " ").split() if token.strip()]
        if not tokens:
            return [0.0]
        return [float(len(token)) for token in tokens[:32]]

    def embed_chunks(self, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
        if not chunks:
            return []

        texts = [chunk.chunk_text for chunk in chunks if chunk.chunk_text]
        if not texts:
            return chunks

        try:
            embeddings = self.embedding_provider.embed_texts(texts)
        except Exception as exc:  # pragma: no cover - defensive path
            self.logger.warning("%s embedding failed; using fallback vectors: %s", self.embedding_provider.__class__.__name__, exc)
            embeddings = [self._fallback_embedding(text) for text in texts]

        for chunk, embedding in zip(chunks, embeddings, strict=False):
            chunk.embedding = embedding
        return chunks

    def save_to_chroma(self, chunks: list[ChunkRecord]) -> None:
        print(self.chroma_store)
        print(json.dumps(self.chroma_store, indent=4))
        if self.chroma_store is None:
            return
        self.chroma_store.save_chunks(chunks)

    def process_chunks(self, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
        embedded_chunks = self.embed_chunks(chunks)
        self.save_to_chroma(embedded_chunks)
        return embedded_chunks


__all__ = ["ChunkEmbedder", "OpenAIEmbeddingProvider", "LocalSentenceTransformerEmbeddingProvider"]
