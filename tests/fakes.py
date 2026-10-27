"""A scripted stand-in for Gemini, so the plumbing can be tested offline."""

import json
from typing import Any, AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptedLlm(BaseLlm):
    """Returns the next scripted step on each call: text, ("tool", args) or a function."""

    script: list[Any] = []
    calls: int = 0

    async def generate_content_async(self, llm_request, stream=False) -> AsyncGenerator[LlmResponse, None]:
        if not self.script:
            raise AssertionError(f"{self.model} was called more times than scripted")
        step = self.script.pop(0)
        self.calls += 1
        if callable(step):
            step = step(llm_request)
        if isinstance(step, str):
            part = types.Part(text=step)
        else:
            name, args = step
            part = types.Part(function_call=types.FunctionCall(name=name, args=args))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def verdict(status="pass", safe_reply=""):
    return json.dumps({"status": status, "reason": "test", "safe_reply": safe_reply})


def script(desk, **scripts):
    """Gives each named agent its own script. 'reviewer' scripts the reviewer."""
    agents = {a.name: a for a in [desk.agent.root_agent, *desk.agent.root_agent.sub_agents]}
    agents["reviewer"] = desk.reviewer.reviewer_agent
    models = {}
    for name, agent in agents.items():
        agent.model = ScriptedLlm(model=f"fake-{name}", script=list(scripts.get(name, [])))
        models[name] = agent.model
    return models
