from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any, Iterator

import gradio as gr
import requests

import os

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "company_logo.svg"
SAMPLE_QUESTIONS = [
    "Summarize the latest budget context for Q3.",
    "What are the key forecast trends across the business units?",
    "Compare actuals and budgets for the latest reporting period.",
    "Explain the main document context around the company's guidance.",
]

CSS = """
body {
    background:
        radial-gradient(circle at top left, rgba(16, 87, 167, 0.14), transparent 22%),
        linear-gradient(180deg, #f6f9fc 0%, #ebf1f8 100%);
    font-family: Inter, "Segoe UI", sans-serif;
}
.gradio-container {
    max-width: 1400px !important;
}
#brand-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 16px 18px;
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(242, 247, 253, 0.98));
    border: 1px solid rgba(23, 71, 122, 0.12);
    box-shadow: 0 20px 45px rgba(14, 48, 92, 0.08);
    margin-bottom: 1rem;
}
#brand-card .brand-title {
    font-size: 2rem;
    font-weight: 800;
    color: #0d2e5c;
    letter-spacing: -0.03em;
    margin: 0;
}
#brand-card .brand-subtitle {
    margin: 0.2rem 0 0;
    color: #557396;
    font-size: 0.98rem;
}
.sample-button {
    border-radius: 999px;
    background: linear-gradient(135deg, #ffffff, #f2f8ff);
    color: #0d2e5c;
    border: 1px solid #cfdded;
    box-shadow: 0 8px 18px rgba(13, 46, 92, 0.06);
    transition: 0.18s ease;
}
.sample-button:hover {
    border-color: #1f72be;
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(13, 46, 92, 0.1);
}
.chatbot {
    border-radius: 22px;
    padding: 0.4rem;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(16, 74, 128, 0.12);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8), 0 14px 30px rgba(13, 46, 92, 0.06);
}
#status-box {
    border-radius: 18px;
    padding: 0.9rem 1rem;
    background: linear-gradient(135deg, #ffffff, #f5f9fe);
    border: 1px solid #d9e5f0;
    box-shadow: 0 12px 26px rgba(13, 46, 92, 0.05);
    color: #244763;
}
#status-box .markdown {
    margin: 0;
}
"""


def _coerce_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not history:
        return []
    return [
        {"role": str(entry.get("role", "user")), "content": str(entry.get("content", ""))}
        for entry in history
        if isinstance(entry, dict) and entry.get("content") is not None
    ]


def _find_available_port(start_port: int = 7860, end_port: int = 7900) -> int:
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue

    raise OSError(f"No free Gradio port available in range {start_port}-{end_port}.")


def _parse_sse_stream(response: requests.Response) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        if raw_line is None:
            continue

        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and event_name is not None and data_lines:
            payload = json.loads("".join(data_lines))
            events.append((event_name, payload))
            event_name = None
            data_lines = []

    if event_name is not None and data_lines:
        payload = json.loads("".join(data_lines))
        events.append((event_name, payload))

    return events


def _status_html(progress_messages: list[str]) -> str:
    if not progress_messages:
        return "### Backend agent status\nWaiting for the orchestrator response..."
    return "### Backend agent status\n" + "\n".join(f"- {message}" for message in progress_messages)


def _stream_orchestrator_response(
    message: str,
    history: list[dict[str, str]] | None,
    api_base_url: str,
) -> Iterator[tuple[list[dict[str, str]], str, list[dict[str, str]]]]:
    if not message or not message.strip():
        return

    current_history = _coerce_history(history)
    current_history.append({"role": "user", "content": message.strip()})
    progress_messages: list[str] = []
    conversation_history = [
        {"role": entry["role"], "content": entry["content"]}
        for entry in current_history[:-1]
        if entry["role"] in {"user", "assistant"}
    ]

    yield current_history, _status_html(progress_messages), current_history

    try:
        response = requests.post(
            f"{api_base_url.rstrip('/')}/orchestrator/ask-openai",
            json={
                "user_question": message.strip(),
                "api_base_url": api_base_url,
                "conversation_history": conversation_history,
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        for event_name, payload in _parse_sse_stream(response):
            if event_name == "status":
                stage = str(payload.get("stage", "")).strip()
                status_text = str(payload.get("message", "")).strip()
                reasoning = payload.get("reasoning")
                if stage == "planning_update" and reasoning:
                    progress_messages.append(f"[planning_update] {reasoning}")
                elif stage:
                    progress_messages.append(f"[{stage}] {status_text}" if status_text else stage)
                elif status_text:
                    progress_messages.append(status_text)
                yield current_history, _status_html(progress_messages), current_history
            elif event_name == "final":
                final_response = str(payload.get("final_response", "")).strip()
                current_history.append({"role": "assistant", "content": final_response})
                yield current_history, f"### Final response\n{final_response}", current_history
                break
            elif event_name == "error":
                error_text = str(payload.get("message", "Unexpected orchestrator error")).strip()
                current_history.append({"role": "assistant", "content": error_text})
                yield current_history, f"### Final response\n{error_text}", current_history
                break
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        current_history.append({"role": "assistant", "content": f"Error calling API: {error_text}"})
        yield current_history, f"### Final response\nError calling API: {error_text}", current_history
    except requests.RequestException as exc:
        error_text = f"Connection error: {exc}"
        current_history.append({"role": "assistant", "content": error_text})
        yield current_history, f"### Final response\n{error_text}", current_history
    except Exception as exc:
        error_text = f"Unexpected error: {exc}"
        current_history.append({"role": "assistant", "content": error_text})
        yield current_history, f"### Final response\n{error_text}", current_history


def _fetch_welcome(api_url: str) -> tuple[list[dict[str, str]], str]:
    try:
        response = requests.get(f"{api_url.rstrip('/')}/orchestrator/welcome", timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        time.sleep(1)
        try:
            response = requests.get(f"{api_url.rstrip('/')}/orchestrator/welcome", timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            return [], "### Backend agent status\nUnable to connect to backend welcome API."

    data = response.json()
    welcome_text = data.get("welcome_message", "")
    overview_text = data.get("data_overview", "")
    if welcome_text or overview_text:
        combined = "\n\n".join(filter(None, [welcome_text, overview_text]))
        return [{"role": "assistant", "content": combined}], "### Backend agent status\nWelcome message loaded."
    return [], "### Backend agent status\nWaiting for the orchestrator response..."


with gr.Blocks() as app:
    with gr.Row(equal_height=True):
        with gr.Column(scale=1):
            gr.Image(
                value=str(LOGO_PATH),
                container=False,
                show_label=False,
                height=96,
                type="filepath",
            )
        with gr.Column(scale=4):
            gr.HTML(
                """
                <div id="brand-card">
                    <div>
                        <p class="brand-title">Financial Analyst Copilot</p>
                        <p class="brand-subtitle">Corporate finance question answering with secure orchestration and grounded insights.</p>
                    </div>
                </div>
                """
            )

    gr.Markdown("### Try one of these sample questions")

    with gr.Row():
        message = gr.Textbox(
            label="Your question",
            placeholder="Ask a finance question about budgets, forecasts, actuals, or company guidance...",
            lines=4,
        )
        api_base_url = gr.Textbox(
            label="API base URL",
            value=DEFAULT_API_BASE_URL,
            info="Set this to your FastAPI backend endpoint.",
        )

    with gr.Row():
        for sample in SAMPLE_QUESTIONS:
            gr.Button(sample, elem_classes=["sample-button"]).click(
                fn=lambda sample_text=sample: sample_text,
                inputs=None,
                outputs=message,
            )

    with gr.Row(equal_height=False):
        with gr.Column(scale=5):
            chatbot = gr.Chatbot(
                value=[],
                label="Finance Conversation",
                height=620,
                elem_classes=["chatbot"],
                buttons=["copy"],
                layout="bubble",
                placeholder="Ask a finance question to begin the conversation...",
            )
            status_box = gr.Markdown(
                "### Backend agent status\nWaiting for the orchestrator response...",
                elem_id="status-box",
            )

        with gr.Column(scale=2):
            send_btn = gr.Button("Send to orchestrator", variant="primary")

    state = gr.State(value=[])

    def _submit_question(message_value: str, history_value: list[dict[str, str]], api_url: str):
        yield from _stream_orchestrator_response(message_value, history_value, api_url)

    send_btn.click(
        fn=_submit_question,
        inputs=[message, state, api_base_url],
        outputs=[chatbot, status_box, state],
    )

    message.submit(
        fn=_submit_question,
        inputs=[message, state, api_base_url],
        outputs=[chatbot, status_box, state],
    )

    app.load(
        fn=_fetch_welcome,
        inputs=[api_base_url],
        outputs=[chatbot, status_box],
    )


if __name__ == "__main__":
    available_port = _find_available_port()
    app.launch(
        server_name="127.0.0.1",
        server_port=available_port,
        share=False,
        theme=gr.themes.Soft(primary_hue=gr.themes.colors.blue),
        css=CSS,
    )
