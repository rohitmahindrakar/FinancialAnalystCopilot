# Financial Analyst Copilot

FinPulseAI - Financial Analyst Copilot is a retrieval-augmented AI assistant for finance workflows. It combines document ingestion, semantic retrieval, structured finance APIs, and orchestrated LLM responses in one repository.

## What this repository includes

- `services/`: FastAPI backend, orchestration routes, RAG services, and business APIs.
- `scripts/`: local app entrypoints (including Streamlit UI) and utility scripts.
- `database/`: SQLite connection layer, models, and CRUD utilities.
- `tests/`: unit and integration-style tests for routing, orchestration, and RAG components.
- `financial-copilot/`: container and Kubernetes deployment assets.

## Quick start (local development)

### 1) Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the backend API

```powershell
.\.venv\Scripts\python.exe -m uvicorn services:app --reload
```

Alternative import path:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api_app:app --reload
```

When the API is running:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health-check`

### 4) Run the Streamlit UI

```powershell
.\.venv\Scripts\streamlit.exe run scripts/streamlit_app.py
```

## Typical ingestion and Q&A workflow

1. Place source files in `notebooks/finance_docs/`.
2. Trigger chunking from the UI sidebar (`Chunk Documents`) or call the endpoint directly:
   - `GET /orchestrator/chunk-documents/true` for local model chunking.
   - `GET /orchestrator/chunk-documents/false` for OpenAI-compatible chunking.
3. Ask questions from the Streamlit chat interface.

## Key API routes

- `GET /health-check`: API and DB readiness check.
- `GET /metadata/tables`: available SQLite tables.
- `GET /users`: list app users.
- `GET /orchestrator/welcome`: startup context and data overview.
- `POST /orchestrator/ask-openai`: streaming orchestrated response.
- `GET /orchestrator/chunk-documents/{internal}`: document chunking and embedding workflow.
- `POST /chroma/query-finance`: semantic retrieval over chunked documents.
- `GET /tools` and `POST /intent/route`: local tool discovery and intent routing.

## Configuration

Common environment variables used in the repo:

- `OPENAI_API_KEY`: required for external model calls.
- `OPENAI_API_BASE`: optional custom OpenAI-compatible base URL.
- `OPENAI_MODEL`: model used for external chunking/orchestration defaults.
- `API_BASE_URL`: Streamlit backend target (default `http://127.0.0.1:8000`).

Create a `.env` file in the repo root when using external providers.

## Tests

Run the test suite from the repository root:

```bash
pytest -q
```

## Deployment assets

For containerized and Kubernetes deployment, see:

- `financial-copilot/README.md`
- `financial-copilot/k8s/`

## Notes

- SQLite database file defaults to `financial_analyst_copilot.db`.
- Chroma persistence is under `database/chroma/`.
- API app export is `services:app` via `services/__init__.py`.
