from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from .chunking import ChunkingHelper
from .chroma_store import ChunkChromaStore
from .embeddings import ChunkEmbedder, LocalSentenceTransformerEmbeddingProvider, OpenAIEmbeddingProvider
from .models import ChunkRecord, IngestionResult
from .providers import ModelProvider
from .readers import DocumentReader

load_dotenv()


DEFAULT_SOURCE_DIR = Path(r"C:\Rohit\Trainings\1_AI_Upskilling_Program_Cohort_6\Capstone_FinancialAnalyst\DocumentsToChunk")
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


def _find_repo_root(start_path: Path) -> Path:
    """Return the nearest ancestor that looks like the repository root."""
    start_path = start_path.expanduser().resolve()
    for candidate in [start_path, *start_path.parents]:
        if (candidate / "services").exists() and (candidate / "requirements.txt").exists():
            return candidate
    return start_path if start_path.is_dir() else start_path.parent


class Injestor:
    """Ingest documents from a folder, chunk them with local Ollama or external openAI model, and return structured results."""

    def __init__(
        self,
        source_dir: Optional[str | Path] = None,
        model: str = DEFAULT_MODEL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        timeout: int = 90,
        logger: Optional[logging.Logger] = None,
        provider: str = "ollama",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        external_model: Optional[str] = None,
        use_external_model: bool = False,
        use_openai_embeddings: bool = False,
        temperature: float = 0.1,
    ) -> None:
        self.source_dir = Path(source_dir or DEFAULT_SOURCE_DIR).expanduser()
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.provider_name = (provider or "ollama").strip().lower()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.external_model = external_model or os.getenv("OPENAI_MODEL") or model
        self.use_external_model = use_external_model or self.provider_name == "openai"
        self.use_openai_embeddings = use_openai_embeddings
        self.temperature = temperature
        self.reader = DocumentReader(logger=self.logger)
        self.provider = ModelProvider(
            model=self.model,
            ollama_url=self.ollama_url,
            timeout=self.timeout,
            logger=self.logger,
            provider=self.provider_name,
            api_key=self.api_key,
            api_base=self.api_base,
            external_model=self.external_model,
            use_external_model=self.use_external_model,
            temperature=self.temperature,
        )
        self.chunking_helper = ChunkingHelper(logger=self.logger)
        repo_root = _find_repo_root(self.source_dir)
        self.chroma_store = ChunkChromaStore(
            persist_directory=repo_root / "database" / "chroma",
            collection_name=f"{self.source_dir.name}_chunks",
            logger=self.logger,
        )
        self.embedding_provider = (
            OpenAIEmbeddingProvider(api_key=self.api_key, api_base=self.api_base)
            if self.use_openai_embeddings
            else LocalSentenceTransformerEmbeddingProvider()
        )
        self.chunk_embedder = ChunkEmbedder(
            embedding_provider=self.embedding_provider,
            chroma_store=self.chroma_store,
            logger=self.logger,
        )
        self.supported_extensions = self.reader.supported_extensions

    async def ingest_documents(self) -> list[IngestionResult]:
        """Read documents from the configured folder, send them to Ollama, and return chunked results."""
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory does not exist: {self.source_dir}")

        document_paths = self._list_documents()
        self.logger.info("Ingesting documents from: %s", self.source_dir)
        if not document_paths:
            self.logger.warning("No supported documents were found in %s", self.source_dir)
            return []
        self.logger.info("Found %d documents to ingest in %s", len(document_paths), self.source_dir)
        tasks = [self._process_document(path) for path in document_paths]
        results = await asyncio.gather(*tasks)
        successful_results = [result for result in results if result is not None]
        self._persist_results(successful_results)
        return successful_results

    def _list_documents(self) -> list[Path]:
        return self.reader.list_documents(self.source_dir)

    async def _process_document(self, path: Path) -> Optional[IngestionResult]:
        self.logger.info("Reading document: %s", path.name)
        text = await asyncio.to_thread(self._read_text, path)
        if not text.strip():
            self.logger.warning("Skipping empty document: %s", path.name)
            return None

        chunks = await self._chunk_text(path.name, text)
        return IngestionResult(
            document_name=path.name,
            source_path=str(path),
            text_length=len(text),
            chunk_count=len(chunks),
            chunks=chunks,
        )

    def _read_text(self, path: Path) -> str:
        """Read plain-text-like documents including PDF and Word files when available."""
        return self.reader.read_text(path)

    def _persist_results(self, results: list[IngestionResult]) -> None:
        all_chunks: list[ChunkRecord] = []
        for result in results:
            all_chunks.extend(result.chunks)

        if not all_chunks:
            return

        self.chunk_embedder.process_chunks(all_chunks)

    async def _chunk_text(self, document_name: str, text: str) -> list[ChunkRecord]:
        self.logger.info("Processing document: %s", document_name)
        response_text = await self._call_ollama(document_name, text)
        if not response_text:
            self.logger.warning("No response content received for %s", document_name)
        else:
            self.logger.debug("Response preview for %s: %s", document_name, response_text[:200])
        parsed_chunks = self.chunking_helper.parse_response(response_text)
        if parsed_chunks:
            return [
                ChunkRecord(
                    document_name=document_name,
                    chunk_index=index,
                    chunk_text=chunk_payload.get("chunk", "").strip(),
                    word_count=int(chunk_payload.get("word_count") or len(chunk_payload.get("chunk", "").split())),
                    headline=str(chunk_payload.get("headline", "")).strip(),
                    summary=str(chunk_payload.get("summary", "")).strip(),
                )
                for index, chunk_payload in enumerate(parsed_chunks)
            ]

        print("Ollama response was not parsable; falling back to deterministic chunking for %s", document_name)
        self.logger.warning("Ollama response was not parsable; falling back to deterministic chunking for %s", document_name)
        return self.chunking_helper.fallback_chunk_text(document_name, text)

    async def _call_ollama(self, document_name: str, text: str) -> str:
        return await self.provider._call_ollama(document_name, text)

    async def _call_local_ollama(self, document_name: str, text: str) -> str:
        return await self.provider._call_local_ollama(document_name, text)

    async def _call_external_model(self, document_name: str, text: str) -> str:
        return await self.provider._call_external_model(document_name, text)

    def _build_prompt(self, document_name: str, text: str) -> str:
        return self.provider._build_prompt(document_name, text)

    def _parse_ollama_response(self, response_text: str) -> list[dict[str, Any]]:
        return self.chunking_helper.parse_response(response_text)

    def _fallback_chunk_text(self, document_name: str, text: str) -> list[ChunkRecord]:
        return self.chunking_helper.fallback_chunk_text(document_name, text)

    def to_dict(self, results: list[IngestionResult]) -> list[dict[str, Any]]:
        """Convert ingestion results to JSON-friendly dictionaries."""
        return [asdict(result) for result in results]


async def main() -> None:
    ingestor = Injestor()
    results = await ingestor.ingest_documents()
    print(json.dumps(ingestor.to_dict(results), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
