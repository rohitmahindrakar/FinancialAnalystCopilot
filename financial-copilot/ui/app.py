from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import scripts.streamlit_app  # noqa: E402, F401
