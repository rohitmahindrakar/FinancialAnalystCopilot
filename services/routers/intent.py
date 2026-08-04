from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException

from ..api_schemas import IntentRouteRequest, IntentRouteResponse

router = APIRouter()

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/v1/chat/completions"


def _load_tool_descriptions() -> dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    tool_path = os.path.join(base_dir, "ollama_tool_descriptions.json")
    try:
        with open(tool_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Tool description file not found: {tool_path}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Tool description file is invalid JSON: {exc}") from exc


def _format_tool_list(tools: list[dict[str, Any]]) -> str:
    lines = []
    for tool in tools:
        lines.append(
            f"- name: {tool.get('name')}, method: {tool.get('method')}, path: {tool.get('path')}, description: {tool.get('description')}"
        )
    return "\n".join(lines)


def _select_intent_route(query: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
    tool_text = _format_tool_list(tools)
    prompt = (
        "You are a local API intent router. Choose the single best tool for the user's question from the "
        "following tool catalog. Respond with valid JSON only, using these keys: tool_name, path, method, description, intent, arguments. "
        "Do not include any extra text."
        "\n\nUser question: "
        f"{query}\n\n"
        "Available tools:\n"
        f"{tool_text}"
        "\n\n"
        "If multiple tools could apply, choose the one that best matches the user's intent. "
        "Arguments should be a JSON object with any detected filters or parameters; otherwise use {}."
    )

    request_payload = {
        "model": "llama2",
        "messages": [
            {"role": "system", "content": "You are a JSON-only router assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }

    data = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama HTTP error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Cannot reach Ollama at {OLLAMA_URL}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from Ollama response: {exc}") from exc

    choices = payload.get("choices")
    if not choices:
        raise HTTPException(status_code=502, detail="Ollama returned no choices.")

    content = choices[0].get("message", {}).get("content", "")
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama response was not valid JSON. "
                f"Response content: {content[:400]}"
            ),
        ) from exc

    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Ollama response JSON must be an object.")

    return result


@router.get("/tools")
def list_tools() -> Any:
    tool_description = _load_tool_descriptions()
    return tool_description.get("tools", [])


@router.post("/intent/route", response_model=IntentRouteResponse)
def route_intent(payload: IntentRouteRequest) -> dict[str, Any]:
    user_query = payload.user_question.strip()
    if not user_query:
        raise HTTPException(status_code=422, detail="user_question cannot be empty")

    tool_description = _load_tool_descriptions()
    tools = tool_description.get("tools", [])
    selected = _select_intent_route(user_query, tools)

    return {
        "tool_name": selected.get("tool_name", ""),
        "tool_path": selected.get("path", ""),
        "tool_method": selected.get("method", ""),
        "description": selected.get("description", ""),
        "intent": selected.get("intent", ""),
        "arguments": selected.get("arguments", {}),
    }
