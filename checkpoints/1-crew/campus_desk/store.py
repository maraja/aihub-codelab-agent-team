"""A pretend college back end: the handbook, student records and bookings.

Everything lives in memory and resets when the server restarts.
"""

import json
import uuid
from pathlib import Path

from .flags import fill_flags

DATA = Path(__file__).parent / "data"


def raw_data() -> str:
    return "\n".join(p.read_text() for p in sorted(DATA.iterdir()))


def handbook_sections() -> list[dict]:
    """Split the handbook into {title, text} sections at each '## ' heading."""
    text = fill_flags((DATA / "handbook.md").read_text())
    sections = []
    for chunk in text.split("\n## ")[1:]:
        title, _, body = chunk.partition("\n")
        sections.append({"title": title.strip(), "text": body.strip()})
    return sections


def students() -> dict[str, dict]:
    rows = json.loads(fill_flags((DATA / "students.json").read_text()))
    return {row["student_id"]: row for row in rows}


def slots() -> dict[str, dict]:
    rows = json.loads((DATA / "slots.json").read_text())
    return {row["slot_id"]: row for row in rows}


BOOKINGS: dict[str, dict] = {}


def add_booking(student_id: str, slot_id: str) -> dict:
    booking = {
        "booking_id": f"B-{uuid.uuid4().hex[:6]}",
        "student_id": student_id,
        "slot_id": slot_id,
    }
    BOOKINGS[booking["booking_id"]] = booking
    return booking


def booked_slot_ids() -> set[str]:
    return {b["slot_id"] for b in BOOKINGS.values()}


def reset() -> None:
    BOOKINGS.clear()
