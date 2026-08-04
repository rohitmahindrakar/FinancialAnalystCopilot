from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI

from services.routers import health_router, chroma_router

app = FastAPI(title="Financial Analyst Copilot Chroma Service", version="0.1.0")
app.include_router(health_router)
app.include_router(chroma_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
