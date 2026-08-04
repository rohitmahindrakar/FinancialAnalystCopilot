# Financial Analyst Copilot

This repository is organized into separate packages for database access, API services, and example scripts.

## Project structure

- `database/`
  - Core SQLite data access layer
  - `connection.py` — connection manager with transaction support
  - `crud.py` — generic `BaseDAO` and table-specific DAO classes
  - `models.py` — typed dataclasses for each table
  - `README.md` — package-specific usage notes

- `services/`
  - FastAPI application and request/response schemas
  - `api_app.py` — FastAPI app entrypoint
  - `api_schemas.py` — Pydantic request/response models
  - `API_DOCUMENTATION.md` — generated API documentation
  - `ollama_tool_descriptions.json` — local tool metadata for intent routing

- `scripts/`
  - Convenience example scripts
  - `example_usage.py` — sample DAO usage demonstration

## Running the API

From the repository root:

```powershell
python -m uvicorn services:app --reload
```

The FastAPI app is exported from `services/__init__.py` as `app`.

## Running the example script

From the repository root:

```powershell
python -m scripts.example_usage
```

## Notes

- The database file is `financial_analyst_copilot.db`.
- The core `database` package is independent of the API layer.
- API routes and schema definitions live under `services`.
- New intent routing endpoints:
  - `GET /tools` — list available Ollama-enabled API tools
  - `POST /intent/route` — select the best tool for a user question via local Ollama
