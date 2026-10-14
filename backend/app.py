"""Vercel entrypoint (vercel.json, service "api"): the MarginArena API as a module-level ASGI app.

Local runs use `uvicorn --factory marginarena.api:create_app` instead; this file only makes the src/ package
importable where the project is not installed, then builds the app once.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from marginarena.api import create_app  # noqa: E402  (needs the path above)

app = create_app()
