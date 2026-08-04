from __future__ import annotations

from fastapi import FastAPI

from services.routers import (
    chroma_router,
    dimensions_router,
    documents_router,
    evaluations_router,
    finance_router,
    health_router,
    intent_router,
    operations_router,
    orchestrator_router,
)

app = FastAPI(title="Financial Analyst Copilot API", version="0.1.0")

app.include_router(health_router)
app.include_router(dimensions_router)
app.include_router(documents_router)
app.include_router(evaluations_router)
app.include_router(finance_router)
app.include_router(operations_router)
app.include_router(intent_router)
app.include_router(chroma_router)
app.include_router(orchestrator_router)
