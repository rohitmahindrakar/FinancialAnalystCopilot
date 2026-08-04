from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow this component to run from the new financial-copilot folder while importing the shared repo code.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from services.rag.injest import main as ingestion_main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(ingestion_main())
