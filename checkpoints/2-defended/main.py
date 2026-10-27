"""The web server Cloud Run runs: ADK's API server plus its chat UI at /dev-ui/."""

import os

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(agents_dir=AGENTS_DIR, web=True, session_service_uri="memory://")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
