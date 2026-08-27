
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
import streamlit as st
import pandas as pd

from models.models import ChartSpec, CitationInfo, FinalFinancialResponse

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "company_logo.svg"
USER_AVATAR = "🧑\u200d💼"
ASSISTANT_AVATAR = "📈"
SAMPLE_QUESTIONS = [
    "Summarize the latest budget context for Q3.",
    "What are the key forecast trends across the business units?",
    "Compare actuals and budgets for the latest reporting period.",
    "Explain the main document context around the company's guidance.",
]

st.set_page_config(page_title="FinPulseAI", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --fp-navy: #0d1b2a;
        --fp-cyan: #44d1c2;
        --fp-ink: #10273e;
        --fp-slate: #4f6782;
        --fp-pearl: #f5f9ff;
        --fp-line: #d8e4f5;
    }

    .stApp {
        font-family: 'IBM Plex Sans', sans-serif;
        background:
            radial-gradient(1200px 500px at -10% -10%, rgba(68, 209, 194, 0.28) 0%, rgba(68, 209, 194, 0) 60%),
            radial-gradient(1000px 500px at 115% 0%, rgba(57, 121, 194, 0.18) 0%, rgba(57, 121, 194, 0) 62%),
            linear-gradient(180deg, #f5f9ff 0%, #eef4fd 100%);
    }

    h1, h2, h3, h4 {
        font-family: 'Sora', sans-serif;
        letter-spacing: -0.02em;
        color: var(--fp-ink);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 6rem;
        max-width: 980px;
    }

    .brand-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.2rem;
        padding: 1rem 1.2rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(9, 33, 61, 0.11);
        border-radius: 20px;
        box-shadow: 0 18px 34px rgba(9, 33, 61, 0.12);
        backdrop-filter: blur(7px);
        animation: rise-in 520ms ease-out;
    }

    .brand-header img {
        width: 68px;
        height: 68px;
        border-radius: 18px;
        box-shadow: 0 12px 24px rgba(19, 76, 133, 0.22);
    }

    .brand-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f2845;
    }

    .brand-subtitle {
        font-size: 0.9rem;
        color: var(--fp-slate);
        max-width: 38rem;
    }

    .status-pill {
        display: inline-block;
        padding: 0.26rem 0.78rem;
        border-radius: 999px;
        background: #e7fff8;
        color: #0b6f4b;
        border: 1px solid rgba(11, 111, 75, 0.2);
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: auto;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35);
        animation: pulse-dot 1.6s ease-in-out infinite;
    }

    .signal-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.65rem;
        margin-bottom: 1.2rem;
    }

    .signal-card {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid var(--fp-line);
        border-radius: 14px;
        padding: 0.65rem 0.8rem;
        box-shadow: 0 10px 22px rgba(10, 42, 77, 0.08);
        animation: rise-in 600ms ease-out;
    }

    .signal-card b {
        display: block;
        color: var(--fp-ink);
        font-size: 0.88rem;
        margin-bottom: 0.08rem;
    }

    .signal-card span {
        color: var(--fp-slate);
        font-size: 0.76rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c213a 0%, #123a5f 58%, #1a4f74 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.14);
    }

    section[data-testid="stSidebar"] * {
        color: #edf4ff !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        color: #0f2845 !important;
        background: #ffffff;
        border-radius: 11px;
        border: 1px solid #b9d0ec;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #f3f8ff;
        border-radius: 12px;
        text-align: left;
        padding: 0.55rem 0.9rem;
        line-height: 1.35;
        white-space: normal;
        transition: all 220ms ease;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: #9fd8ff;
        background: rgba(255, 255, 255, 0.22);
        transform: translateY(-1px);
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.08);
        overflow: hidden;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] details {
        background: rgba(255, 255, 255, 0.08);
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background: rgba(12, 33, 58, 0.92) !important;
        color: #edf4ff !important;
        padding: 0.45rem 0.65rem;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary:focus,
    section[data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary {
        background: rgba(21, 60, 97, 0.96) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
        fill: #cce6ff !important;
    }

    section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
        background: rgba(8, 28, 49, 0.6);
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        padding: 0.35rem 0.55rem 0.65rem;
    }

    div[data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.93);
        border: 1px solid #d9e4f2;
        border-radius: 18px;
        box-shadow: 0 12px 28px rgba(9, 33, 61, 0.08);
        margin-bottom: 0.6rem;
    }

    div[data-testid="stChatInput"] textarea {
        border-radius: 14px !important;
        border: 1px solid #bdd3ed !important;
        box-shadow: 0 6px 16px rgba(10, 42, 77, 0.09);
    }

    @media (max-width: 900px) {
        .signal-row {
            grid-template-columns: 1fr;
        }
        .brand-title {
            font-size: 1.35rem;
        }
        .brand-subtitle {
            font-size: 0.84rem;
        }
    }

    @keyframes rise-in {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse-dot {
        0%, 100% {
            transform: scale(1);
            opacity: 0.95;
        }
        50% {
            transform: scale(1.03);
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []
if "welcome_loaded" not in st.session_state:
    st.session_state.welcome_loaded = False
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "selected_user_label" not in st.session_state:
    st.session_state.selected_user_label = None
if "selected_user_role_code" not in st.session_state:
    st.session_state.selected_user_role_code = None
if "user_selection_confirmed" not in st.session_state:
    st.session_state.user_selection_confirmed = False
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "conversation_summaries" not in st.session_state:
    st.session_state.conversation_summaries = []
if "conversation_history_error" not in st.session_state:
    st.session_state.conversation_history_error = None
if "conversation_history_user_id" not in st.session_state:
    st.session_state.conversation_history_user_id = None
if "conversation_load_error" not in st.session_state:
    st.session_state.conversation_load_error = None

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
    st.markdown("### FinPulseAI")
    st.caption("Real-time financial pulse checks powered by a grounded orchestration engine.")
    if st.session_state.user_selection_confirmed and st.session_state.selected_user_label:
        st.caption(f"Active user: {st.session_state.selected_user_label}")
        if st.button("Switch user", use_container_width=True):
            st.session_state.history = []
            st.session_state.welcome_loaded = False
            st.session_state.pending_question = None
            st.session_state.selected_user_id = None
            st.session_state.selected_user_label = None
            st.session_state.selected_user_role_code = None
            st.session_state.user_selection_confirmed = False
            st.session_state.conversation_id = None
            st.session_state.conversation_summaries = []
            st.session_state.conversation_history_error = None
            st.session_state.conversation_history_user_id = None
            st.rerun()
    st.divider()

    api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)

    st.divider()
    with st.expander("Try a sample question", expanded=False):
        for idx, sample in enumerate(SAMPLE_QUESTIONS):
            if st.button(sample, key=f"sample_{idx}", use_container_width=True):
                st.session_state.pending_question = sample

    # Add a button to call the backend chunk-documents endpoint and show streaming updates.
    with st.expander("Chunk Documents", expanded=False):
        internal = st.checkbox("Use internal model", value=False, key="chunk_docs_internal")
        chunk_stream_placeholder = st.empty()
        chunk_final_placeholder = st.empty()
        if st.button("📄 Chunk documents", use_container_width=True):
            status_messages: list[str] = []

            def render_status_block() -> None:
                if not status_messages:
                    return
                chunk_stream_placeholder.info("\n".join(status_messages[-8:]))

            def handle_chunk_event(event: str, payload: dict[str, Any]) -> None:
                message = str(payload.get("message") or payload.get("status") or "").strip()
                if event == "status" and message:
                    status_messages.append(message)
                    render_status_block()
                elif event == "final":
                    final_message = message or "Document chunking completed."
                    chunk_final_placeholder.success(final_message)
                elif event == "error":
                    error_message = message or str(payload.get("error") or "Chunking failed.")
                    chunk_final_placeholder.error(error_message)

            try:
                response = requests.get(
                    f"{api_base_url.rstrip('/')}/orchestrator/chunk-documents/{internal}",
                    stream=True,
                    timeout=180,
                )
                response.raise_for_status()

                event_name: str | None = None
                data_lines: list[str] = []

                for raw_line in response.iter_lines(decode_unicode=True):
                    if raw_line is None:
                        continue

                    line = raw_line.strip()

                    # SSE event boundary: parse accumulated data payload.
                    if not line:
                        if event_name is not None and data_lines:
                            json_payload = "".join(data_lines)
                            payload = json.loads(json_payload)
                            if isinstance(payload, dict):
                                handle_chunk_event(event_name, payload)
                        event_name = None
                        data_lines = []
                        continue

                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        continue

                    if line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].strip())
                        continue

                    # Fallback for NDJSON streams: {"event": "status", "data": {...}}
                    parsed_line = json.loads(line)
                    if isinstance(parsed_line, dict):
                        event = str(parsed_line.get("event") or "").strip()
                        data = parsed_line.get("data")
                        if event and isinstance(data, dict):
                            handle_chunk_event(event, data)

                # Flush final SSE event if stream ended without trailing blank line.
                if event_name is not None and data_lines:
                    json_payload = "".join(data_lines)
                    payload = json.loads(json_payload)
                    if isinstance(payload, dict):
                        handle_chunk_event(event_name, payload)

                if not status_messages:
                    chunk_stream_placeholder.info("Chunk request sent. Waiting for backend status events.")

            except requests.HTTPError as exc:
                detail = exc.response.text if exc.response is not None else str(exc)
                chunk_final_placeholder.error(f"Chunk API error: {detail}")
            except requests.RequestException as exc:
                chunk_final_placeholder.error(f"Chunk API connection error: {exc}")
            except json.JSONDecodeError as exc:
                chunk_final_placeholder.error(f"Failed to decode stream payload: {exc}")
            except Exception as exc:  # noqa: BLE001 - surface unexpected stream handling issues
                chunk_final_placeholder.error(f"Unexpected chunk streaming error: {exc}")
                
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.welcome_loaded = False
        st.session_state.conversation_id = None
        st.rerun()

st.markdown('<div class="brand-header">', unsafe_allow_html=True)
col_logo, col_brand, col_status = st.columns([1, 5, 2])
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
with col_brand:
    st.markdown(
        "<div class='brand-title'>FinPulseAI</div>"
        "<div class='brand-subtitle'>Track the health and movement of company financial performance with grounded, source-backed intelligence.</div>",
        unsafe_allow_html=True,
    )
with col_status:
    st.markdown("<span class='status-pill'>● Connected</span>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="signal-row">
        <div class="signal-card"><b>Performance Pulse</b><span>Monitor shifts in budget, forecast, and actuals.</span></div>
        <div class="signal-card"><b>Risk Drift</b><span>Spot early variance patterns before they widen.</span></div>
        <div class="signal-card"><b>Narrative Context</b><span>Link every answer to grounded document evidence.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)


def fetch_app_users() -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            f"{api_base_url.rstrip('/')}/users",
            params={"limit": 200, "offset": 0},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        raw_items: Any
        if isinstance(payload, dict):
            raw_items = payload.get("items", [])
        elif isinstance(payload, list):
            raw_items = payload
        else:
            return [], "Users API returned an unexpected response format."

        users: list[dict[str, Any]] = []
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            user_id = entry.get("user_id")
            if user_id is None:
                continue

            display_name = (
                entry.get("display_name")
                or entry.get("username")
                or entry.get("email")
                or f"User {user_id}"
            )
            role_code = entry.get("role_code")
            role_name = entry.get("role_name")

            role_obj = entry.get("role")
            if isinstance(role_obj, dict):
                if role_code is None:
                    role_code = role_obj.get("role_code")
                if role_name is None:
                    role_name = role_obj.get("role_name") or role_obj.get("name")

            if role_name is None:
                role_name = entry.get("role") if isinstance(entry.get("role"), str) else None

            if role_code is None and role_name is not None:
                role_code = role_name

            users.append(
                {
                    "user_id": str(user_id),
                    "label": str(display_name),
                    "role_code": str(role_code) if role_code is not None else None,
                    "role_name": str(role_name) if role_name else "Unknown Role",
                }
            )

        users.sort(key=lambda user: user["label"].lower())
        return users, None
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        return [], f"Unable to load users from backend: {detail}"
    except requests.RequestException as exc:
        return [], f"Unable to connect to users API: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected parse issues
        return [], f"Unexpected error while loading users: {exc}"


def fetch_welcome_message() -> str:
    try:
        welcome_response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/welcome", timeout=20)
        welcome_response.raise_for_status()
        welcome_data = welcome_response.json()
        welcome_text = welcome_data.get("welcome_message", "")
        overview_text = welcome_data.get("data_overview", "")
        combined_text = "\n\n".join(filter(None, [welcome_text, overview_text]))
        return combined_text or "Welcome to FinPulseAI. Ask a question to get started."
    except requests.HTTPError as exc:
        error_details = exc.response.text if exc.response is not None else str(exc)
        return f"Unable to load welcome message from backend: {error_details}"
    except requests.RequestException as exc:
        return f"Unable to connect to backend welcome API: {exc}"


def fetch_user_conversation_history(user_id: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            f"{api_base_url.rstrip('/')}/users/{user_id}/conversation_history",
            params={"limit": 200, "offset": 0},
            timeout=20,
        )
        if response.status_code == 404:
            return [], None

        response.raise_for_status()
        payload = response.json()

        raw_items: Any
        if isinstance(payload, dict):
            raw_items = payload.get("items", [])
        elif isinstance(payload, list):
            raw_items = payload
        else:
            return [], "Conversation history API returned an unexpected response format."

        history_records = [entry for entry in raw_items if isinstance(entry, dict)]
        return history_records, None
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        return [], f"Unable to load conversation history: {detail}"
    except requests.RequestException as exc:
        return [], f"Unable to connect to conversation history API: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected parsing issues
        return [], f"Unexpected error while loading conversation history: {exc}"


def fetch_conversation_by_id(conversation_id: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            f"{api_base_url.rstrip('/')}/conversation_history/{conversation_id}",
            params={"limit": 200, "offset": 0},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        raw_items: Any
        if isinstance(payload, dict):
            raw_items = payload.get("items", [])
        elif isinstance(payload, list):
            raw_items = payload
        else:
            return [], "Conversation API returned an unexpected response format."

        records = [entry for entry in raw_items if isinstance(entry, dict)]
        return records, None
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        return [], f"Unable to load selected conversation: {detail}"
    except requests.RequestException as exc:
        return [], f"Unable to connect to conversation API: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected parsing issues
        return [], f"Unexpected error while loading selected conversation: {exc}"


def _extract_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            text = _extract_text(item)
            if text:
                fragments.append(text)
        return "\n".join(fragments).strip()

    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"].strip()

        if isinstance(value.get("message"), str):
            return value["message"].strip()

        if isinstance(value.get("answer"), str):
            return value["answer"].strip()

        if isinstance(value.get("final_answer"), str):
            return value["final_answer"].strip()

        if value.get("final_answer") is not None:
            nested_final = _extract_text(value.get("final_answer"))
            if nested_final:
                return nested_final

        content = value.get("content")
        if content is not None:
            nested_content = _extract_text(content)
            if nested_content:
                return nested_content

        if value.get("type") in {"input_text", "output_text"}:
            nested = _extract_text(value.get("text"))
            if nested:
                return nested

    return ""


def _resolve_history_role(record: dict[str, Any], item_payload: Any) -> str | None:
    role_value = str(record.get("role") or "").strip().lower()
    item_type = str(record.get("item_type") or "").strip().lower()

    payload_role = ""
    payload_type = ""
    if isinstance(item_payload, dict):
        payload_role = str(item_payload.get("role") or "").strip().lower()
        payload_type = str(item_payload.get("type") or "").strip().lower()

    for candidate in (role_value, payload_role):
        if candidate in {"user", "assistant"}:
            return candidate

    merged_markers = " ".join(
        marker
        for marker in (role_value, item_type, payload_type, payload_role)
        if marker
    )

    # Persisted OpenAI agent history can include values like input_text/output_text/message.
    # Map these to chat roles so resumed conversations show both sides correctly.
    if any(token in merged_markers for token in ["assistant", "output", "response", "model"]):
        return "assistant"
    if any(token in merged_markers for token in ["user", "input", "prompt"]):
        return "user"

    return None


def _convert_history_record_to_chat_message(record: dict[str, Any]) -> dict[str, Any] | None:
    item_payload = record.get("item_json")

    if isinstance(item_payload, str):
        try:
            item_payload = json.loads(item_payload)
        except json.JSONDecodeError:
            item_payload = {"text": item_payload}

    role = _resolve_history_role(record, item_payload)
    if role is None:
        return None

    text = _extract_text(item_payload)
    if not text:
        return None

    message: dict[str, Any] = {"role": role, "text": text}

    if role == "assistant":
        candidate_payload: Any = item_payload
        if isinstance(item_payload, dict):
            candidate_payload = (
                item_payload.get("final_response")
                or item_payload.get("response")
                or item_payload.get("content")
                or item_payload
            )

        structured_response = _coerce_final_financial_response(candidate_payload)

        if structured_response is None and isinstance(text, str) and text:
            structured_response = _coerce_final_financial_response(text)

        if structured_response is not None:
            message["text"] = structured_response.answer or text
            message["response"] = structured_response.model_dump(mode="json")

            chart_payload = _extract_chart_payload(
                candidate_payload,
                item_payload if isinstance(item_payload, dict) else {},
            )
            chart_spec = _coerce_chart_spec(chart_payload)
            if chart_spec is not None:
                message["chart_spec"] = chart_spec.model_dump(mode="json")

    return message


def _format_history_datetime(value: Any) -> str:
    parsed = _parse_history_datetime(value)
    if parsed is not None:
        return parsed.strftime("%Y-%m-%d %H:%M")

    if value is None:
        return "Unknown date"

    raw = str(value).strip()
    return raw or "Unknown date"


def _parse_history_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    # Accept ISO values from SQLite/FastAPI payloads and normalize for display.
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _group_conversation_summaries(summaries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {"Today": [], "Yesterday": [], "Older": []}
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for summary in summaries:
        activity_dt = summary.get("last_activity_dt")
        if isinstance(activity_dt, datetime):
            normalized = activity_dt.astimezone() if activity_dt.tzinfo else activity_dt
            activity_date = normalized.date()
            if activity_date == today:
                groups["Today"].append(summary)
            elif activity_date == yesterday:
                groups["Yesterday"].append(summary)
            else:
                groups["Older"].append(summary)
        else:
            groups["Older"].append(summary)

    return groups


def build_conversation_summaries(history_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in history_records:
        conversation_id = record.get("conversation_id")
        if conversation_id is None:
            continue
        grouped.setdefault(str(conversation_id), []).append(record)

    summaries: list[dict[str, Any]] = []
    for conversation_id, records in grouped.items():
        ordered_records = sorted(
            records,
            key=lambda row: int(row.get("sequence_no") or 0),
        )
        messages: list[dict[str, Any]] = []
        for record in ordered_records:
            message = _convert_history_record_to_chat_message(record)
            if message:
                messages.append(message)

        last_user_message = next(
            (msg["text"] for msg in reversed(messages) if msg["role"] == "user"),
            "",
        )
        if messages:
            preview = (last_user_message or messages[-1]["text"]).replace("\n", " ").strip()
        else:
            fallback_title = str(ordered_records[-1].get("title") or "").strip()
            preview = fallback_title or f"Conversation {conversation_id[:8]}"

        if len(preview) > 48:
            preview = f"{preview[:45]}..."

        last_row = ordered_records[-1]
        last_activity = (
            last_row.get("last_activity_at")
            or last_row.get("updated_at")
            or last_row.get("created_at")
            or ""
        )
        last_activity_dt = _parse_history_datetime(last_activity)
        turns = sum(1 for msg in messages if msg["role"] == "user")
        title = preview if preview else f"Conversation {conversation_id[:8]}"
        date_label = _format_history_datetime(last_activity)
        label = f"{title} | {date_label}"

        summaries.append(
            {
                "conversation_id": conversation_id,
                "messages": messages,
                "label": label,
                "title": title,
                "date_label": date_label,
                "turns": turns,
                "last_activity_dt": last_activity_dt,
                "last_activity": str(last_activity) if last_activity is not None else "",
            }
        )

    summaries.sort(
        key=lambda item: item["last_activity_dt"] if isinstance(item.get("last_activity_dt"), datetime) else datetime.min,
        reverse=True,
    )
    return summaries


with st.spinner("Loading available users..."):
    available_users, users_error = fetch_app_users()
if not st.session_state.user_selection_confirmed:
    st.subheader("Choose a user profile")
    st.caption("Select your user identity to start a conversation in FinPulseAI.")

    if users_error:
        st.error(users_error)
        if st.button("Retry loading users", use_container_width=True):
            st.rerun()

    selected_label: str | None = None
    option_to_user: dict[str, dict[str, Any]] = {}
    if available_users:
        option_labels = ["Select a user..."]
        for user in available_users:
            role_name = user.get("role_name") or "Unknown Role"
            option_label = f"{user['label']} ({role_name}) (ID: {user['user_id']})"
            option_labels.append(option_label)
            option_to_user[option_label] = user
        selected_label = st.selectbox(
            "Available users",
            options=option_labels,
            index=0,
            help="This list is loaded from the backend /users API.",
        )
    else:
        st.info("No users are currently available from the /users API.")

    can_continue = bool(available_users) and selected_label is not None and selected_label != "Select a user..."
    if st.button("Continue to FinPulseAI", type="primary", disabled=not can_continue):
        selected_user = option_to_user[selected_label]
        st.session_state.selected_user_id = selected_user["user_id"]
        st.session_state.selected_user_label = selected_user["label"]
        st.session_state.selected_user_role_code = selected_user.get("role_code")
        st.session_state.user_selection_confirmed = True
        st.session_state.history = []
        st.session_state.welcome_loaded = False
        st.session_state.pending_question = None
        st.session_state.conversation_id = None
        st.rerun()

    st.stop()


def _coerce_final_financial_response(final_response: Any) -> FinalFinancialResponse | None:
    if isinstance(final_response, FinalFinancialResponse):
        return final_response

    if isinstance(final_response, str):
        stripped = final_response.strip()
        if not stripped:
            return FinalFinancialResponse(answer="", citations=[])
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return FinalFinancialResponse(answer=stripped, citations=[])
        final_response = parsed

    if not isinstance(final_response, dict):
        return None

    if isinstance(final_response.get("final_answer"), dict):
        nested = _coerce_final_financial_response(final_response.get("final_answer"))
        if nested is not None:
            return nested

    answer = final_response.get("answer")
    if answer is None:
        answer = final_response.get("final_answer")
    if answer is None:
        answer = ""

    raw_citations = final_response.get("citations")
    if raw_citations is None:
        raw_citations = final_response.get("citationInformation")
    if raw_citations is None:
        raw_citations = []

    citations: list[CitationInfo] = []
    if isinstance(raw_citations, list):
        for citation in raw_citations:
            try:
                citations.append(CitationInfo.model_validate(citation))
            except Exception:
                continue

    return FinalFinancialResponse(answer=str(answer), citations=citations)


def _coerce_chart_spec(chart_payload: Any) -> ChartSpec | None:
    if chart_payload is None:
        return None

    if isinstance(chart_payload, ChartSpec):
        return chart_payload

    if isinstance(chart_payload, str):
        try:
            parsed = json.loads(chart_payload)
        except json.JSONDecodeError:
            return None
        chart_payload = parsed

    if isinstance(chart_payload, dict):
        try:
            return ChartSpec.model_validate(chart_payload)
        except Exception:
            return None

    return None


def _extract_chart_payload(final_response: Any, payload: dict[str, Any]) -> Any:
    top_level = payload.get("chartSpec") or payload.get("chart")
    if top_level is not None:
        return top_level

    if isinstance(final_response, dict):
        nested = (
            final_response.get("chartSpec")
            or final_response.get("chart")
            or final_response.get("chart_spec")
        )
        if nested is not None:
            return nested

        nested_final = final_response.get("final_answer")
        if isinstance(nested_final, dict):
            return (
                nested_final.get("chartSpec")
                or nested_final.get("chart")
                or nested_final.get("chart_spec")
            )

    return None


def stream_orchestrator_response(response: requests.Response, status: Any) -> tuple[FinalFinancialResponse | None, ChartSpec | None]:
    """Consume the backend SSE stream, updating the status widget, and return the final answer."""
    event_name: str | None = None
    data_lines: list[str] = []
    final_response: FinalFinancialResponse | None = None
    final_chart_spec: ChartSpec | None = None

    def handle_event(name: str, payload: dict[str, Any]) -> None:
        nonlocal final_response
        nonlocal final_chart_spec

        try:
            if name == "status":
                message = payload.get("message", "")
                stage = payload.get("stage", "")
                reasoning = payload.get("reasoning")

                if st.session_state.conversation_id is None and payload.get("conversation_id") is not None:
                    st.session_state.conversation_id = payload.get("conversation_id")

                if stage == "planning_update" and reasoning:
                    text = f"Planning: {reasoning}"
                elif stage and message:
                    text = f"{stage.replace('_', ' ').title()}: {message}"
                else:
                    text = message
                if text:
                    status.update(label=text)
                    status.write(text)
            elif name == "final":
                raw_final_response = payload.get("final_response", "")
                if (
                    isinstance(raw_final_response, dict)
                    and "citations" not in raw_final_response
                    and "citationInformation" not in raw_final_response
                    and payload.get("citationInformation") is not None
                ):
                    raw_final_response = {
                        **raw_final_response,
                        "citationInformation": payload.get("citationInformation"),
                    }
                coerced = _coerce_final_financial_response(raw_final_response)
                if coerced is None:
                    final_response = FinalFinancialResponse(answer=str(raw_final_response), citations=[])
                else:
                    final_response = coerced

                final_chart_spec = _coerce_chart_spec(
                    _extract_chart_payload(raw_final_response, payload)
                )
            elif name == "error":
                error_text = payload.get("message") or payload.get("error_message") or "Unexpected orchestrator error"
                final_response = FinalFinancialResponse(answer=error_text, citations=[])
                final_chart_spec = None
        except Exception as exc:
            final_response = FinalFinancialResponse(answer=f"Unexpected error: {exc}", citations=[])
            final_chart_spec = None

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            json_str = ''.join(data_lines)
            handle_event(event_name, json.loads(json_str))
            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        json_str = ''.join(data_lines)
        handle_event(event_name, json.loads(json_str))

    return final_response, final_chart_spec


def ask_orchestrator(user_question: str, status: Any) -> tuple[FinalFinancialResponse, ChartSpec | None] | str:
    try:
        # conversation_history = [
        #     {"role": item["role"], "content": item["text"]} for item in st.session_state.history[:-1]
        # ]
        response = requests.post(
            f"{api_base_url.rstrip('/')}/orchestrator/ask-openai",
            json={
                "user_question": user_question,
                "api_base_url": api_base_url,
                "user_id": st.session_state.selected_user_id,
                "role_code": st.session_state.selected_user_role_code,
                #"conversation_history": conversation_history,
                "conversation_id": st.session_state.conversation_id
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()
        final_answer, chart_spec = stream_orchestrator_response(response, status)
        if final_answer is None:
            return "The orchestrator returned no final response."
        return final_answer, chart_spec
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        return f"Error calling API: {error_text}"
    except requests.RequestException as exc:
        return f"Connection error: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the chat
        return f"Unexpected error: {exc}"


def render_response(response: FinalFinancialResponse, chart_spec: ChartSpec | None = None) -> None:
    st.markdown(response.answer)

    if chart_spec:
        data = {"category": chart_spec.categories}
        for series in chart_spec.series:
            data[series.name] = series.values

        df = pd.DataFrame(data)
        st.subheader(chart_spec.title)

        if chart_spec.chart_type == "line":
            st.line_chart(df, x="category")
        elif chart_spec.chart_type == "bar":
            st.bar_chart(df, x="category")
        elif chart_spec.chart_type == "scatter":
            st.scatter_chart(df, x="category")

    if not response.citations:
        return

    with st.expander("Citation Information", expanded=False):
        for citation in response.citations:
            label = citation.label or citation.citation_id
            st.markdown(f"**[{citation.citation_type.title()}] {label}**")

            if citation.citation_type == "document":
                details: list[str] = []
                if citation.document_name:
                    details.append(f"Document: {citation.document_name}")
                if citation.page_number is not None:
                    details.append(f"Page: {citation.page_number}")
                if citation.chunk_id:
                    details.append(f"Chunk ID: {citation.chunk_id}")
                if citation.document_link:
                    details.append(f"Link: {citation.document_link}")
                if details:
                    st.caption(" | ".join(details))

            elif citation.citation_type == "database":
                details = []
                if citation.database_source:
                    details.append(f"Source: {citation.database_source}")
                if citation.query_name:
                    details.append(f"Query: {citation.query_name}")
                if citation.query_summary:
                    details.append(f"Summary: {citation.query_summary}")
                if details:
                    st.caption(" | ".join(details))

            elif citation.citation_type == "calculation":
                if citation.calculation_name:
                    st.caption(f"Calculation: {citation.calculation_name}")


if st.session_state.user_selection_confirmed and st.session_state.selected_user_id:
    should_refresh_history = (
        st.session_state.conversation_history_user_id != st.session_state.selected_user_id
    )

    if should_refresh_history:
        with st.spinner("Loading conversation history..."):
            history_records, history_error = fetch_user_conversation_history(
                st.session_state.selected_user_id
            )
        st.session_state.conversation_summaries = build_conversation_summaries(history_records)
        st.session_state.conversation_history_error = history_error
        st.session_state.conversation_history_user_id = st.session_state.selected_user_id

    with st.sidebar:
        st.divider()
        with st.expander("Conversation History", expanded=True):
            if st.session_state.conversation_history_error:
                st.error(st.session_state.conversation_history_error)
            if st.session_state.conversation_load_error:
                st.error(st.session_state.conversation_load_error)

            if st.button("Refresh history", key="refresh_conversation_history", use_container_width=True):
                st.session_state.conversation_history_user_id = None
                st.rerun()

            summaries = st.session_state.conversation_summaries
            if st.button("Start a new conversation", key="start_new_conversation", use_container_width=True):
                st.session_state.history = []
                st.session_state.welcome_loaded = False
                st.session_state.conversation_id = None
                st.rerun()

            grouped_summaries = _group_conversation_summaries(summaries)
            has_any_history = any(grouped_summaries[group] for group in ["Today", "Yesterday", "Older"])
            if not has_any_history:
                st.caption("No previous conversations found.")

            for group_name in ["Today", "Yesterday", "Older"]:
                group_entries = grouped_summaries[group_name]
                if not group_entries:
                    continue

                st.caption(group_name)
                for summary in group_entries:
                    button_label = f"{summary['title']} | {summary['date_label']}"
                    is_active = summary["conversation_id"] == st.session_state.conversation_id
                    if is_active:
                        st.markdown(f"**Active: {button_label}**")
                    if st.button(
                        "Open" if is_active else button_label,
                        key=f"open_conversation_{summary['conversation_id']}",
                        use_container_width=True,
                        type="secondary" if is_active else "tertiary",
                        help=f"Conversation ID: {summary['conversation_id']}",
                    ):
                        with st.spinner("Loading selected conversation..."):
                            selected_records, selected_error = fetch_conversation_by_id(summary["conversation_id"])

                        if selected_error:
                            st.session_state.conversation_load_error = selected_error
                        else:
                            ordered_records = sorted(
                                selected_records,
                                key=lambda row: int(row.get("sequence_no") or 0),
                            )
                            loaded_messages: list[dict[str, Any]] = []
                            for record in ordered_records:
                                message = _convert_history_record_to_chat_message(record)
                                if message:
                                    loaded_messages.append(message)

                            st.session_state.history = loaded_messages
                            st.session_state.welcome_loaded = True
                            st.session_state.conversation_id = summary["conversation_id"]
                            st.session_state.conversation_load_error = None
                        st.rerun()

if not st.session_state.welcome_loaded:
    st.session_state.history.append({"role": "assistant", "text": fetch_welcome_message()})
    st.session_state.welcome_loaded = True

for item in st.session_state.history:
    avatar = USER_AVATAR if item["role"] == "user" else ASSISTANT_AVATAR
    with st.chat_message(item["role"], avatar=avatar):
        structured_response = item.get("response")
        history_chart_spec = _coerce_chart_spec(item.get("chart_spec"))
        if item["role"] == "assistant" and structured_response:
            coerced = _coerce_final_financial_response(structured_response)
            if coerced:
                render_response(coerced, history_chart_spec)
            else:
                st.markdown(item["text"])
        else:
            st.markdown(item["text"])

prompt = st.chat_input("Ask a business finance question...")
if not prompt and st.session_state.pending_question:
    prompt = st.session_state.pending_question
st.session_state.pending_question = None

if prompt:
    st.session_state.history.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.status("Contacting FinPulseAI agent...", expanded=True) as status:
            final_answer = ask_orchestrator(prompt, status)
            status.update(label="Response ready", state="complete", expanded=False)
    
        if isinstance(final_answer, tuple):
            final_response, chart_spec = final_answer
            render_response(final_response, chart_spec)
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "text": final_response.answer,
                    "response": final_response.model_dump(mode="json"),
                    "chart_spec": chart_spec.model_dump(mode="json") if chart_spec else None,
                }
            )
        else:
            st.markdown(final_answer)
            st.session_state.history.append({"role": "assistant", "text": final_answer})
