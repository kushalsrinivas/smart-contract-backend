import os
from typing import List

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app


def _parse_origins(value: str | None) -> List[str]:
    if not value:
        return ["*"]
    return [o.strip() for o in value.split(",") if o.strip()]


# Directory that contains your ADK agents (must include __init__.py and agent.py)
AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent")

# Configure CORS via env var or default to wildcard for local dev
# Example: export ALLOWED_ORIGINS="http://localhost:3000,https://yourapp.com"
ALLOWED_ORIGINS = _parse_origins(os.environ.get("ALLOWED_ORIGINS"))

# Optionally serve the built-in ADK web UI
SERVE_WEB_INTERFACE = os.environ.get("ADK_SERVE_WEB", "true").lower() in ("1", "true", "yes")

# Build the FastAPI app with CORS configured
app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("server:app", host=host, port=port, reload=os.environ.get("RELOAD", "0") == "1")


