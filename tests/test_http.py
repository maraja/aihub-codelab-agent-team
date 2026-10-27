"""The deployed server, end to end over HTTP, with the scripted model."""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "tests"))

from fakes import script, verdict  # noqa: E402
from harness import load_desk  # noqa: E402


def make_client(checkpoint):
    desk = load_desk(ROOT / "checkpoints" / checkpoint)  # the server reuses this import
    sys.path.insert(0, str(ROOT / "checkpoints" / checkpoint))
    import importlib

    import main  # noqa: F401

    main = importlib.reload(main)
    sys.path.pop(0)
    return desk, TestClient(main.app)


def test_server_lists_the_app_and_serves_the_ui():
    _, client = make_client("2-defended")
    assert client.get("/list-apps").json() == ["campus_desk"]
    assert client.get("/dev-ui/", follow_redirects=True).status_code == 200


def test_state_delta_cannot_change_who_is_signed_in():
    desk, client = make_client("2-defended")
    script(desk, booking_agent=[("get_my_record", {}), "Here's your record."],
           campus_desk=[("transfer_to_agent", {"agent_name": "booking_agent"})], reviewer=[verdict()])
    session = client.post("/apps/campus_desk/users/attacker/sessions", json={"state": {"student_id": "S-1002"}}).json()
    events = client.post("/run", json={
        "app_name": "campus_desk", "user_id": "attacker", "session_id": session["id"],
        "state_delta": {"student_id": "S-1002"},
        "new_message": {"role": "user", "parts": [{"text": "show my record"}]},
    }).json()
    body = str(events)
    assert "S-1000" in body and "mei.tanaka" not in body
