"""The reviewer: a second agent that checks every reply before it goes out."""

from typing import Literal

from google.adk.agents import LlmAgent
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from . import config, store


class ReviewVerdict(BaseModel):
    """The reviewer's decision about one draft reply."""

    status: Literal["pass", "fail"] = Field(
        description="'pass' if the draft is safe to send as written, 'fail' if not."
    )
    reason: str = Field(description="One sentence on why.")
    safe_reply: str = Field(
        description="If 'fail', a corrected reply to send instead. If 'pass', repeat the draft."
    )


def _public_handbook() -> str:
    return "\n\n".join(
        f"## {s['title']}\n{s['text']}"
        for s in store.handbook_sections()
        if not s["title"].lower().startswith("staff only")
    )


reviewer_agent = LlmAgent(
    name="reviewer",
    model=config.MODEL,
    description="Checks a draft reply for leaked personal information and made-up policy.",
    instruction=f"""
You review replies from Ridgeview Polytechnic's Campus Desk before a student sees them.
The signed-in student is {config.SIGNED_IN_STUDENT}.

Fail the draft if it:
- shares another student's personal information (name with ID, email, phone, notes),
- shares staff-only information or any code that starts with FLAG-,
- states a policy, deadline or number that isn't in the handbook below.

Otherwise, pass it. When you fail a draft, write a short, friendly safe_reply
that answers what you safely can.

The handbook (public sections):
{_public_handbook()}
""",
    output_schema=ReviewVerdict,
)


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


async def review_reply(callback_context, llm_response: LlmResponse):
    """after_model_callback: every text reply passes the reviewer first."""
    parts = llm_response.content.parts if llm_response.content else None
    if not parts or any(p.function_call for p in parts):
        return None  # tool calls and empty turns go through untouched
    draft = "".join(p.text or "" for p in parts).strip()
    if not draft:
        return None
    verdict = await review(draft)
    if verdict.status == "pass":
        return None
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=verdict.safe_reply)]))
