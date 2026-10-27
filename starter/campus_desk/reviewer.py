"""The reviewer: a second agent that checks every reply before it goes out."""

from typing import Literal

from google.adk.agents import LlmAgent
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from . import config, store

# Step 7a: add the ReviewVerdict schema here.


def _public_handbook() -> str:
    return "\n\n".join(
        f"## {s['title']}\n{s['text']}"
        for s in store.handbook_sections()
        if not s["title"].lower().startswith("staff only")
    )


# Step 7b: add the reviewer agent here.


async def review(draft: str) -> ReviewVerdict:
    """Runs the reviewer agent on one draft and returns its verdict."""
    runner = InMemoryRunner(agent=reviewer_agent, app_name="reviewer")
    session = await runner.session_service.create_session(app_name="reviewer", user_id="desk")
    message = types.Content(role="user", parts=[types.Part(text=f"Draft reply:\n{draft}")])
    final_text = ""
    async for event in runner.run_async(user_id="desk", session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)
    return ReviewVerdict.model_validate_json(final_text)


# Step 7c: add the review_reply callback here.
