from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import requests


class ModelProvider:
    """Coordinate local and external model calls for chunk generation."""

    def __init__(
        self,
        *,
        model: str,
        ollama_url: str,
        timeout: int,
        logger: Optional[logging.Logger] = None,
        provider: str = "ollama",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        external_model: Optional[str] = None,
        use_external_model: bool = False,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.provider = (provider or "ollama").strip().lower()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.external_model = external_model or os.getenv("OPENAI_MODEL") or model
        self.use_external_model = use_external_model or self.provider == "openai"
        self.temperature = temperature

    async def _call_ollama(self, document_name: str, text: str) -> str:
        if self.use_external_model:
            return await self._call_external_model(document_name, text)
        return await self._call_local_ollama(document_name, text)

    async def _call_local_ollama(self, document_name: str, text: str) -> str:
        prompt = self._build_prompt(document_name, text)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }

        self.logger.debug("Sending local Ollama request for %s", document_name)

        def _post() -> requests.Response:
            return requests.post(self.ollama_url, json=payload, timeout=self.timeout)

        try:
            response = await asyncio.to_thread(_post)
            response.raise_for_status()
            response_payload = response.json()
            self.logger.debug("Received local Ollama response for %s", document_name)
        except requests.RequestException as exc:
            self.logger.warning("Ollama request failed for %s: %s", document_name, exc)
            return ""
        except ValueError as exc:
            self.logger.warning("Ollama returned invalid JSON for %s: %s", document_name, exc)
            return ""

        return str(response_payload.get("response", "")).strip()

    async def _call_external_model(self, document_name: str, text: str) -> str:
        prompt = self._build_prompt(document_name, text)
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("OPENAI_API_KEY is not configured. Add it to your .env file.")
            raise RuntimeError("OPENAI_API_KEY is not configured. Add it to your .env file.")

        model_name = self.external_model or self.model
        litellm_model = model_name if "/" in model_name else f"{self.provider}/{model_name}"

        self.logger.info("Sending external model request for %s using %s", document_name, litellm_model)

        try:
            from litellm import acompletion

            response = await acompletion(
                model=litellm_model,
                api_key=api_key,
                api_base=self.api_base,
                temperature=self.temperature,
                timeout=self.timeout,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content if getattr(response, "choices", None) else None
            return str(content or "").strip()
        except Exception as exc:  # pragma: no cover - defensive path
            self.logger.exception("External model request failed for %s: %s", document_name, exc)
            return ""

    def _build_prompt(self, document_name: str, text: str) -> str:
        preview = text[:20000]
        return f"""You are a document chunking assistant for RAG.

                Task:
                - Split the document named '{document_name}' into overlapping text chunks.
                - Aim for an average chunk size of 100 words.
                - Make adjacent chunks overlap by about 20 words.
                - Preserve the original wording and meaning.
                - Do not return code.
                - Return only valid JSON in the following structure:
                [
                  {{"headline": "short heading", "summary": "one or two sentence summary", "chunk": "chunk text here", "word_count": 100}},
                  {{"headline": "short heading", "summary": "one or two sentence summary", "chunk": "chunk text here", "word_count": 95}}
                ]

                Document content:
                {preview}
                """


__all__ = ["ModelProvider"]
