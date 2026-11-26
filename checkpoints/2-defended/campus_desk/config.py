"""Settings shared by every agent in the Campus Desk."""

import os

from google.adk.models import Gemini
from google.genai import types

# Gemini runs through Gemini Enterprise Agent Platform (formerly Vertex AI)
# in your own Google Cloud project.
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "true")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")


class _Gemini(Gemini):
    """Gemini with a time limit: a call that stalls is cut off after a minute and tried again."""

    async def generate_content_async(self, llm_request, stream=False):
        llm_request.config = llm_request.config or types.GenerateContentConfig()
        llm_request.config.http_options = llm_request.config.http_options or types.HttpOptions()
        llm_request.config.http_options.timeout = 60_000  # milliseconds
        async for response in super().generate_content_async(llm_request, stream):
            yield response


MODEL = _Gemini(
    model=os.environ.get("CAMPUS_DESK_MODEL", "gemini-3.8-flash"),
    retry_options=types.HttpRetryOptions(attempts=3, initial_delay=1),
)

# The Campus Desk is a kiosk that's already signed in as one student.
# Identity comes from the server, never from what someone types in the chat.
SIGNED_IN_STUDENT = "S-1000"
