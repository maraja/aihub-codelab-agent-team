"""Hard rules, enforced in code. The reviewer is a model and can be fooled;
these checks can't be talked out of anything."""

import re

from google.adk.models.llm_response import LlmResponse
from google.genai import types

from . import config, store
from .flags import FLAG_PATTERN

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")

BLOCKED = "Sorry, I can't share that. I can help with handbook questions and your own advising appointments."


def _leaks(text: str) -> bool:
    if FLAG_PATTERN.search(text):
        return True
    my_email = store.students()[config.SIGNED_IN_STUDENT]["email"]
    return any(email.group(0) != my_email for email in _EMAIL.finditer(text))


def block_secrets(callback_context, llm_response: LlmResponse):
    """after_model_callback: replace any reply that contains a flag or someone else's email."""
    parts = llm_response.content.parts if llm_response.content else None
    if not parts:
        return None
    text = " ".join(p.text or "" for p in parts) + " ".join(
        str(p.function_call.args) for p in parts if p.function_call
    )
    if _leaks(text):
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=BLOCKED)]))
    return None
