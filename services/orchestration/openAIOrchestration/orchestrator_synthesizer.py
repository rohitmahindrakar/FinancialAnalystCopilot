from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from services.orchestration.openAIOrchestration.orchestration_common import get_openai_client, OPENAI_MODEL
from services.models.models import OpenAIPlanResult


class ResponseSynthesizer:
    """Formats conversation context and synthesizes the final natural-language answer from tool results."""

    @staticmethod
    def format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return "No prior conversation history provided."

        lines: list[str] = []
        for entry in history:
            role = str(entry.get("role", "user")).strip() or "user"
            content = str(entry.get("content", "")).strip()
            if content:
                lines.append(f"{role.title()}: {content}")

        return "\n".join(lines)

    @staticmethod
    def extract_ranked_evidence(tool_results: list[dict[str, Any]]) -> str:
        evidence_sections: list[str] = []
        ranked_results = [result for result in tool_results if isinstance(result, dict) and result.get("rerank") is True and result.get("results")]

        if ranked_results:
            for result in ranked_results:
                chunks = result.get("results", []) or []
                if not chunks:
                    continue
                lines = []
                for index, chunk in enumerate(chunks, start=1):
                    document = str(chunk.get("document") or chunk.get("text") or chunk.get("content") or "")
                    document = re.sub(r"\s+", " ", document).strip()
                    if not document:
                        continue
                    reason = str(chunk.get("reason") or "")
                    if reason:
                        lines.append(f"{index}. {document} [reason: {reason}]")
                    else:
                        lines.append(f"{index}. {document}")
                if lines:
                    evidence_sections.append("Ranked evidence (most relevant first):\n" + "\n".join(lines))

        if evidence_sections:
            return "\n\n".join(evidence_sections)

        fallback_results = [result for result in tool_results if isinstance(result, dict) and result.get("results")]
        if fallback_results:
            lines: list[str] = []
            for result in fallback_results[:1]:
                for index, chunk in enumerate(result.get("results", []) or [], start=1):
                    document = str(chunk.get("document") or chunk.get("text") or chunk.get("content") or "")
                    document = re.sub(r"\s+", " ", document).strip()
                    if document:
                        lines.append(f"{index}. {document}")
            if lines:
                return "Retrieved evidence:\n" + "\n".join(lines)

        return ""

    def build_prompt(
        self,
        user_question: str,
        conversation_history: list[dict[str, str]],
        tool_results: list[dict[str, Any]],
        plan: OpenAIPlanResult,
    ) -> str:
        history_text = self.format_history(conversation_history)
        results_text = "\n\n".join(json.dumps(result, indent=2) for result in tool_results)
        tool_plan = json.dumps(plan.tools or [], indent=2)
        ranked_evidence_text = self.extract_ranked_evidence(tool_results)

        return (
            "You are a finance assistant. Use the tool execution results as the source of truth for the answer. "
            "Prioritize the ranked evidence section when it is present, and use the top-ranked chunks as the primary support for your answer. "
            "Summarize the current user question only using the returned tool data and the prior conversation context. "
            "If there is no supporting data in the tool outputs, say so clearly and avoid inventing numbers.\n\n"
            f"Current user question: {user_question}\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Planner tool plan:\n{tool_plan}\n\n"
            f"Tool execution results:\n{results_text}\n\n"
            f"Ranked evidence:\n{ranked_evidence_text}\n\n"
            "Return only a concise, well-structured final answer suitable for the UI."
        )

    def synthesize(
        self,
        user_question: str,
        conversation_history: list[dict[str, str]],
        tool_results: list[dict[str, Any]],
        plan: OpenAIPlanResult,
    ) -> str:
        client = get_openai_client()
        prompt = self.build_prompt(user_question, conversation_history, tool_results, plan)

        async def _generate() -> str:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful finance assistant. Base the answer only on the tool results and previous chat context. "
                            "Avoid fabricating numbers or facts."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.0,
                max_tokens=512,
            )
            return str(response.choices[0].message.content or "")

        return asyncio.run(_generate())

