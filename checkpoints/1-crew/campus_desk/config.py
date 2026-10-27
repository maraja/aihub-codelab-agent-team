"""Settings shared by every agent in the Campus Desk."""

import os

# Gemini runs through Vertex AI in your own Google Cloud project.
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "true")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

MODEL = os.environ.get("CAMPUS_DESK_MODEL", "gemini-3.8-flash")

# The Campus Desk is a kiosk that's already signed in as one student.
# Identity comes from the server, never from what someone types in the chat.
SIGNED_IN_STUDENT = "S-1000"
