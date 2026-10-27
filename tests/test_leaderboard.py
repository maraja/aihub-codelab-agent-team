import hashlib
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def client(monkeypatch, room="lab"):
    monkeypatch.setenv("LEADERBOARD_ROOM", room)
    sys.path.insert(0, str(ROOT / "leaderboard"))
    import main

    main = importlib.reload(main)
    sys.path.pop(0)
    return TestClient(main.app)


def h(flag):
    return hashlib.sha256(flag.encode()).hexdigest()


def test_full_round(monkeypatch):
    c = client(monkeypatch)
    assert c.post("/api/register", json={"room": "lab", "handle": "sam", "url": "https://sam.run.app",
                                         "flag_hashes": [h("FLAG-aaaaaaaaaa")]}).status_code == 200
    assert c.post("/api/eval", json={"room": "lab", "handle": "sam", "passed": 7, "total": 13}).status_code == 200
    assert c.post("/api/eval", json={"room": "lab", "handle": "sam", "passed": 12, "total": 13}).status_code == 200

    wrong = c.post("/api/capture", json={"room": "lab", "attacker": "mei", "target": "sam", "flag": "FLAG-bbbbbbbbbb"})
    assert wrong.status_code == 400
    right = c.post("/api/capture", json={"room": "lab", "attacker": "mei", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    assert right.status_code == 200
    again = c.post("/api/capture", json={"room": "lab", "attacker": "mei", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    assert again.json()["message"] == "You already have that one."

    board = c.get("/api/board").json()
    assert board["evals"][0] == {"handle": "sam", "best": 92, "latest": 92, "runs": 2}
    assert board["attackers"] == [{"handle": "mei", "points": 1}]
    assert board["targets"][0]["lost"] == 1
    assert "flag_hashes" not in str(board)
    assert c.get("/").status_code == 200


def test_room_code_and_handles_are_checked(monkeypatch):
    c = client(monkeypatch)
    assert c.post("/api/eval", json={"room": "nope", "handle": "sam", "passed": 1, "total": 2}).status_code == 403
    assert c.post("/api/eval", json={"room": "lab", "handle": "Sam K!", "passed": 1, "total": 2}).status_code == 400
    assert c.post("/api/eval", json={"room": "lab", "handle": "sam", "passed": 3, "total": 2}).status_code == 400


def test_no_self_captures(monkeypatch):
    c = client(monkeypatch)
    c.post("/api/register", json={"room": "lab", "handle": "sam", "url": "https://x.run.app", "flag_hashes": [h("FLAG-aaaaaaaaaa")]})
    r = c.post("/api/capture", json={"room": "lab", "attacker": "sam", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    assert r.status_code == 400
