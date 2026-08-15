
from openai import AsyncOpenAI
import os
from typing import Any
from fastapi import HTTPException
import json


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def event_stream_line(event: str, payload: dict[str, Any]) -> str:
    # print("original payload: ", payload)
    # print("json: ", json.dumps(payload))
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

def get_openai_client() -> AsyncOpenAI:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured in the .env file.")

    return AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
