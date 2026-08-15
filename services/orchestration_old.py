from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

import requests
from fastapi import HTTPException


def _load_tool_descriptions() -> dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    tool_path = os.path.join(base_dir, "services", "ollama_tool_descriptions.json")
    try:
        with open(tool_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Tool description file not found: {tool_path}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Tool description file is invalid JSON: {exc}") from exc


def _format_tool_list(tools: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for tool in tools:
        lines.append(
            "- name: {name}, method: {method}, path: {path}, description: {description}".format(
                name=tool.get("name", ""),
                method=tool.get("method", ""),
                path=tool.get("path", ""),
                description=tool.get("description", ""),
            )
        )
    return "\n".join(lines)


def _select_intent_route(query: str, tools: list[dict[str, Any]], tool_description: dict[str, Any]) -> dict[str, Any]:
    tool_text = _format_tool_list(tools)
    overview_text = tool_description.get("overview", "")
    prompt = (
        "You are an API intent router for a financial analyst assistant. "
        "Choose the best tools needed to answer user's questions from the following tool catalog. "
        "If the question does not match with any tool, return the appropriate response for the users question."
        "If the question needs multiple tools to get to the answer, return the list of tools to be called in the correct sequence."
        "Respond with valid JSON only, using these keys: tool_name, path, method, description, intent, arguments. "
        "Do not include any extra text."
        "\n\nDecision rules:"
        "\n1. Use Chroma chunk retrieval tools (query_finance_chunks / /chroma/query-finance) when the user asks for contextual understanding, summaries, document passages, narrative explanations, background, or asks questions that are best answered from chunked document context."
        "\n2. Use SQL-backed finance tools when the user asks for numerical facts, metrics, totals, budgets, forecasts, actuals, KPIs, periods, accounts, business units, or other structured financial data that lives in the finance database."
        "\n3. Prefer Chroma for broad business-context questions with richer document context, and prefer SQL for explicit financial metric or record lookups."
        "\n4. If the request clearly needs both sources, return the tool that best matches the primary intent of the question."
        "\n5. Arguments should be a JSON object with any detected filters or parameters; otherwise use {}."
    )
    if overview_text:
        prompt += f"\n\nData overview:\n{overview_text}"
    prompt += f"\n\nUser question: {query}\n\nAvailable tools:\n{tool_text}"

    logging.info(f"Router prompt:\n{prompt}")

    request_payload = {
        "model": "gemma3:270m",
        "messages": [
            {"role": "system", "content": "You are a JSON-only router assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }

    request_data = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            payload = json.loads(response_body)
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama HTTP error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Cannot reach Ollama at http://127.0.0.1:11434/v1/chat/completions: {exc.reason}") from exc
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


def build_tool_request(api_base_url: str, tool_route: dict[str, Any]) -> dict[str, Any]:
    path = tool_route.get("path", "") or tool_route.get("tool_path", "")
    args = dict(tool_route.get("arguments") or {})

    path_params = re.findall(r"\{([^}]+)\}", path)
    for param in path_params:
        if param in args:
            path = path.replace(f"{{{param}}}", str(args.pop(param)))

    url = f"{api_base_url.rstrip('/')}{path}"
    method = str(tool_route.get("method") or tool_route.get("tool_method") or "GET").upper()

    if method in {"GET", "DELETE"}:
        return {"method": method, "url": url, "params": args, "json": None}

    return {"method": method, "url": url, "params": None, "json": args}


def invoke_tool_route(api_base_url: str, tool_route: dict[str, Any]) -> dict[str, Any]:
    request_args = build_tool_request(api_base_url, tool_route)
    response = requests.request(
        method=request_args["method"],
        url=request_args["url"],
        params=request_args["params"],
        json=request_args["json"],
        timeout=30,
    )
    response.raise_for_status()

    try:
        body: Any = response.json()
    except ValueError:
        body = response.text

    return {"status_code": response.status_code, "body": body}


def format_tool_response(tool_result: dict[str, Any]) -> str:
    body = tool_result.get("body")
    if isinstance(body, (dict, list)):
        return json.dumps(body, indent=2)
    return str(body)


def select_route_for_query(user_query: str) -> dict[str, Any]:
    tool_description = _load_tool_descriptions()
    tools = tool_description.get("tools", [])
    return _select_intent_route(user_query, tools, tool_description)
