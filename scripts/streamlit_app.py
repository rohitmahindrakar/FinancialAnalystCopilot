
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "company_logo.svg"
USER_AVATAR = "🧑\u200d💼"
ASSISTANT_AVATAR = "💠"
SAMPLE_QUESTIONS = [
    "Summarize the latest budget context for Q3.",
    "What are the key forecast trends across the business units?",
    "Compare actuals and budgets for the latest reporting period.",
    "Explain the main document context around the company's guidance.",
]

st.set_page_config(page_title="Financial Analyst Copilot", page_icon="💠", layout="wide")

st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(180deg, #f4f8fb 0%, #eef4fa 100%);
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 6rem;
        max-width: 900px;
    }
    .brand-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding: 0.9rem 1.25rem;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(13, 46, 92, 0.12);
        border-radius: 16px;
        box-shadow: 0 10px 28px rgba(13, 46, 92, 0.08);
    }
    .brand-header img {
        width: 64px;
        height: 64px;
        border-radius: 16px;
    }
    .brand-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0d2e5c;
    }
    .brand-subtitle {
        font-size: 0.9rem;
        color: #456587;
    }
    .status-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        background: #e5f3ec;
        color: #1c7a4e;
        font-size: 0.78rem;
        font-weight: 600;
        margin-left: auto;
    }
    section[data-testid="stSidebar"] {
        background: #0d2e5c;
    }
    section[data-testid="stSidebar"] * {
        color: #eaf1fb !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        color: #0d2e5c !important;
        background: #ffffff;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.25);
        color: #eaf1fb;
        border-radius: 10px;
        text-align: left;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: #7fb2e8;
        background: rgba(255, 255, 255, 0.16);
    }
    div[data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #dbe7f3;
        border-radius: 16px;
        box-shadow: 0 6px 16px rgba(13, 46, 92, 0.05);
        margin-bottom: 0.6rem;
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

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
    st.markdown("### Financial Analyst Copilot")
    st.caption("Grounded finance Q&A powered by a backend orchestrator agent.")
    st.divider()

    api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)

    st.divider()
    st.markdown("**Try a sample question**")
    for idx, sample in enumerate(SAMPLE_QUESTIONS):
        if st.button(sample, key=f"sample_{idx}", use_container_width=True):
            st.session_state.pending_question = sample

    #add a button to call a backend API \chunk-documents\{internal}, and shows the streaming response below the button
    st.markdown("**Chunk documents**")
    if st.button("📄 Chunk documents", use_container_width=True):
        internal = st.checkbox("Use internal model", value=False)
        response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/chunk-documents/{internal}", stream=True)
        for line in response.iter_lines():
            if line:
                #write a method to capture the streaming response json, that has the format {"event": "status", "data": {"message": "chunking in progress"}}, and displays it in a block below the button, and if the event is "final", display the final message in a success message box
                try:
                    decoded_line = line.decode("utf-8")
                    parsed_line = json.loads(decoded_line)
                    event = parsed_line.get("event")
                    data = parsed_line.get("data", {})
                    message = data.get("message", "")
                    if event == "status":
                        st.info(message)
                    elif event == "final":
                        st.success(message)
                except json.JSONDecodeError:
                    st.error(f"Failed to decode JSON from line: {line}")
                except Exception as e:
                    st.error(f"An error occurred while processing the line: {e}")
                #st.text(line.decode("utf-8"))
                
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.welcome_loaded = False
        st.rerun()

st.markdown('<div class="brand-header">', unsafe_allow_html=True)
col_logo, col_brand, col_status = st.columns([1, 5, 2])
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=64)
with col_brand:
    st.markdown(
        "<div class='brand-title'>Financial Analyst Copilot</div>"
        "<div class='brand-subtitle'>Ask business finance questions and get grounded, source-backed answers.</div>",
        unsafe_allow_html=True,
    )
with col_status:
    st.markdown("<span class='status-pill'>● Connected</span>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


def fetch_welcome_message() -> str:
    try:
        welcome_response = requests.get(f"{api_base_url.rstrip('/')}/orchestrator/welcome", timeout=20)
        welcome_response.raise_for_status()
        welcome_data = welcome_response.json()
        welcome_text = welcome_data.get("welcome_message", "")
        overview_text = welcome_data.get("data_overview", "")
        combined_text = "\n\n".join(filter(None, [welcome_text, overview_text]))
        return combined_text or "Welcome to Financial Analyst Copilot. Ask a question to get started."
    except requests.HTTPError as exc:
        error_details = exc.response.text if exc.response is not None else str(exc)
        return f"Unable to load welcome message from backend: {error_details}"
    except requests.RequestException as exc:
        return f"Unable to connect to backend welcome API: {exc}"


def stream_orchestrator_response(response: requests.Response, status: Any) -> str | None:
    """Consume the backend SSE stream, updating the status widget, and return the final answer."""
    event_name: str | None = None
    data_lines: list[str] = []
    final_answer: str | None = None

    def handle_event(name: str, payload: dict[str, Any]) -> None:
        nonlocal final_answer
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
            final_answer = payload.get("final_response", "")
        elif name == "error":
            final_answer = payload.get("message", "Unexpected orchestrator error")

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            json_str = ''.join(data_lines)#.replace("'", '"')
            handle_event(event_name, json.loads(json_str))
            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        json_str = ''.join(data_lines).replace("'", '"')
        handle_event(event_name, json.loads(json_str))

    return final_answer


def ask_orchestrator(user_question: str, status: Any) -> str:
    try:
        # conversation_history = [
        #     {"role": item["role"], "content": item["text"]} for item in st.session_state.history[:-1]
        # ]
        response = requests.post(
            f"{api_base_url.rstrip('/')}/orchestrator/ask-openai",
            json={
                "user_question": user_question,
                "api_base_url": api_base_url,
                #"conversation_history": conversation_history,
                "conversation_id": st.session_state.conversation_id
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()
        final_answer = stream_orchestrator_response(response, status)
        return final_answer or "The orchestrator returned no final response."
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        return f"Error calling API: {error_text}"
    except requests.RequestException as exc:
        return f"Connection error: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the chat
        return f"Unexpected error: {exc}"


if not st.session_state.welcome_loaded:
    st.session_state.history.append({"role": "assistant", "text": fetch_welcome_message()})
    st.session_state.welcome_loaded = True
    st.session_state.conversation_id = None

for item in st.session_state.history:
    avatar = USER_AVATAR if item["role"] == "user" else ASSISTANT_AVATAR
    with st.chat_message(item["role"], avatar=avatar):
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
        with st.status("Contacting Financial Analyst Copilot agent...", expanded=True) as status:
            final_answer = ask_orchestrator(prompt, status)
            status.update(label="Response ready", state="complete", expanded=False)
        st.markdown(final_answer)

    st.session_state.history.append({"role": "assistant", "text": final_answer})
