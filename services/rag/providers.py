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
        tokenSize: Optional[int] = 500,
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
        self.tokenSize = tokenSize

    async def _call_ai_chunk_text(self, document_name: str, text: str) -> str:
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
        #preview = text[:20000]
        return f"""You are a document chunking assistant for RAG.

                Task:
                - Split the document named '{document_name}' into overlapping text chunks.
                - Aim for an average chunk size of '{self.tokenSize}' words.
                - Make adjacent chunks overlap by about {self.tokenSize // 10} words.
                - Preserve the original wording and meaning.
                - Do not return code.
                - For each chunk, you should provide a headline, a summary, original text, and the metadata extracted from the chunk.
                - Together your chunks should represent the entire document with overlap.
                - Output format

                    Return only valid JSON.

                    Do not return Markdown, code fences, comments, explanations, introductory text, or trailing text.

                    Return a JSON object with one property named chunks.

                    The chunks property must contain an array of chunk objects.

                    Each chunk object must contain exactly these properties:

                    headline
                    summary
                    chunk_text
                    metadata_facts

                    Use this exact structure:

                    {{
                    "chunks": [
                    {{
                    "headline": "string",
                    "summary": "string",
                    "chunk_text": "string",
                    "word_count": "integer",
                    "metadata_facts": {{
                    "key": "value"
                    }}
                    }}
                    ]
                    }}

                Validation checklist

                Before returning the response, verify that:

                The response is valid JSON.
                The root object contains only the chunks property.
                Every chunk contains exactly headline, summary, chunk_text, and metadata_facts.
                Every metadata_facts value is a dictionary object.
                metadata_facts keys use lowercase snake_case.
                metadata_facts contains only facts explicitly supported by the chunk.
                Make sure important named entities have not been removed or generalized.
                chunk_text exactly matches text from the source document.
                Separate employees or unrelated topics have not been mixed.
                The chunks collectively cover the document.
                No commentary appears outside the JSON.

                Metadata requirements

                The metadata_facts property must be a dictionary object containing structured facts explicitly stated in the chunk.

                Represent each fact as a meaningful key-value pair.

                Use lowercase snake_case keys.

                Examples of useful keys include:
                - company name
                - business unit
                - period
                - university
                - job title
                - current salary
                - employee id
                - date of birth

                Use the most specific key that accurately describes the fact.

                Example metadata:

                {{
                "employee_name": "Alice Johnson",
                "job_title": "Data Scientist",
                "universities": [
                "Carnegie Mellon University"
                ],
                "degrees": [
                "Master of Science"
                ],
                "section": "Education"
                }}

                Facts that must be extracted when present

                Extract the following whenever they explicitly appear:

                Company names → company_name or organization
                Business units → business_unit
                Person names → employee_name or person_name
                Analyst names → analyst_name
                Employee identifiers → employee_id
                Universities and schools → university
                Departments → department
                Job titles → job_title
                Companies and organizations → organization
                Office or geographic locations → location
                Degrees → degree
                Certifications → certification
                Projects → project_name
                Products → product_name
                Policies → policy_name
                Dates → a specific key such as effective_date, start_date, or graduation_date
                Document sections → section
                Other exact identifiers → a descriptive lowercase snake_case key
                
                Metadata rules
                Use one metadata_facts entry for each fact.
                Use lowercase snake_case keys.
                Use the same key consistently across chunks.
                Preserve exact capitalization for proper-name values.
                Extract only information explicitly supported by the chunk or its directly applicable parent heading.
                Do not infer, guess, classify, or invent facts.
                Do not put summaries or complete paragraphs in metadata.
                Do not omit a fact merely because it already appears in the headline or summary.
                Multiple facts may use the same key.
                Do not add a key when its value is unknown.
                Use strings for single values.
                Use arrays for multiple values of the same type.
                Use numbers only when the source clearly expresses a numeric value.
                Use booleans only when the source explicitly expresses a true-or-false fact.
                Do not place summaries, explanations, or complete paragraphs in metadata.
                Do not use vague keys such as data, info, value, or other.
                Use consistent keys for the same type of fact across all chunks.
                Do not include source or type unless those values are explicitly provided as part of the document content; they will be added separately by the application.
                When no useful structured facts are present, return an empty metadata object.


                Document content:
                {text}
                """


__all__ = ["ModelProvider"]
