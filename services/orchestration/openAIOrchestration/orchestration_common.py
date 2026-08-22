
from openai import AsyncOpenAI
import os
from typing import Any
from fastapi import HTTPException
import json
from pydantic import BaseModel


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

#models tried
#gpt-4.1-mini
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def event_stream_line(event: str, payload: dict[str, Any]) -> str:
    # print("original payload: ", payload)
    # print("json: ", json.dumps(payload, default=_json_default))
    #return f"event: {event}\ndata: {json.dumps(payload, default=_json_default)}\n\n"
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

def get_openai_client() -> AsyncOpenAI:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured in the .env file.")

    return AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
