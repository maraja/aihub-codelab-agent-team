"""Tools the Campus Desk agents can call.

These are written the quick way, the way a lot of first versions are.
Some of them trust the model more than they should. You'll find out which
ones in the red-team round.
"""

import re

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
        text = f"{section['title']} {section['text']}".lower()
        score = sum(text.count(w) for w in words if len(w) > 2)
        if score:
            scored.append((score, section))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return {"sections": [section for _, section in scored[:3]]}


def lookup_student(student_id: str) -> dict:
    """Looks up a student's record by their student ID.

    Args:
        student_id: The student's ID, for example S-1000.
    """
    record = store.students().get(student_id)
    if record is None:
        return {"error": f"No student with ID {student_id}."}
    return record


def list_open_slots() -> dict:
    """Lists the advising appointment slots that are still open this week."""
    taken = store.booked_slot_ids()
    return {"slots": [s for s in store.slots().values() if s["slot_id"] not in taken]}


def book_appointment(student_id: str, slot_id: str) -> dict:
    """Books an advising appointment for a student.

    Args:
        student_id: The ID of the student the appointment is for.
        slot_id: The slot to book, for example A-101.
    """
    if slot_id not in store.slots():
        return {"error": f"There's no slot {slot_id}."}
    if slot_id in store.booked_slot_ids():
        return {"error": f"Slot {slot_id} is already taken."}
    return {"booked": store.add_booking(student_id, slot_id)}
