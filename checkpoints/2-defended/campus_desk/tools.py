"""Tools the Campus Desk agents can call, after the red-team round.

Each tool gives the model only what the signed-in student is allowed to see,
and takes the student's identity from the server, not from the model.
"""

import re

from google.adk.tools import FunctionTool, ToolContext

from . import store

_WORD = re.compile(r"[a-z]+")


def search_handbook(query: str) -> dict:
    """Searches the student handbook and returns the most relevant sections.

    Args:
        query: What the student is asking about, in a few words.
    """
    words = set(_WORD.findall(query.lower()))
    scored = []
    for section in store.handbook_sections():
        if section["title"].lower().startswith("staff only"):
            continue  # students never need staff-only sections, so the tool never returns them
        text = f"{section['title']} {section['text']}".lower()
        score = sum(text.count(w) for w in words if len(w) > 2)
        if score:
            scored.append((score, section))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return {"sections": [section for _, section in scored[:3]]}


def get_my_record(tool_context: ToolContext) -> dict:
    """Gets the signed-in student's own record: program, advisor and contact details."""
    record = store.students()[tool_context.state["student_id"]]
    return {k: record[k] for k in ("student_id", "name", "program", "email", "advisor")}


def list_open_slots() -> dict:
    """Lists the advising appointment slots that are still open this week."""
    taken = store.booked_slot_ids()
    slots = []
    for s in store.slots().values():
        if s["slot_id"] in taken:
            continue
        slot = {k: s[k] for k in ("slot_id", "advisor", "day", "time")}
        if s["note"]:
            # Text other people wrote is data, not instructions. Label it that way.
            slot["advisor_note_untrusted"] = s["note"]
        slots.append(slot)
    return {"slots": slots}


def book_appointment(slot_id: str, tool_context: ToolContext) -> dict:
    """Books an advising appointment for the signed-in student.

    Args:
        slot_id: The slot to book, for example A-101.
    """
    if slot_id not in store.slots():
        return {"error": f"There's no slot {slot_id}."}
    if slot_id in store.booked_slot_ids():
        return {"error": f"Slot {slot_id} is already taken."}
    return {"booked": store.add_booking(tool_context.state["student_id"], slot_id)}


# A person has to approve every booking before it happens.
book_appointment_tool = FunctionTool(book_appointment, require_confirmation=True)
