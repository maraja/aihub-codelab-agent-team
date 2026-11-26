import hashlib
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def client(monkeypatch, room="lab", admin="teach"):
    monkeypatch.setenv("LEADERBOARD_ROOM", room)
    monkeypatch.setenv("LEADERBOARD_ADMIN", admin)
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
    assert board["attackers"] == [{"handle": "mei", "points": 1, "flags": 1, "vault": []}]
    assert board["targets"][0]["lost"] == 1
    assert "flag_hashes" not in str(board)
    assert c.get("/").status_code == 200


def test_each_flag_scores_once_per_desk(monkeypatch):
    c = client(monkeypatch)
    c.post("/api/register", json={"room": "lab", "handle": "sam", "url": "https://sam.run.app",
                                  "flag_hashes": [h("FLAG-aaaaaaaaaa"), h("FLAG-cccccccccc")]})
    c.post("/api/capture", json={"room": "lab", "attacker": "mei", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    late = c.post("/api/capture", json={"room": "lab", "attacker": "kai", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    assert late.status_code == 200
    assert late.json()["message"] == "mei already scored that flag from sam. Look for another one."
    other = c.post("/api/capture", json={"room": "lab", "attacker": "kai", "target": "sam", "flag": "FLAG-cccccccccc"})
    assert other.json()["message"] == "Capture confirmed: kai took a flag from sam."

    board = c.get("/api/board").json()
    assert {r["handle"]: r["points"] for r in board["attackers"]} == {"mei": 1, "kai": 1}
    assert board["targets"][0]["lost"] == 2


def test_room_code_and_handles_are_checked(monkeypatch):
    c = client(monkeypatch)
    assert c.post("/api/eval", json={"room": "nope", "handle": "sam", "passed": 1, "total": 2}).status_code == 403
    assert c.post("/api/eval", json={"room": "lab", "handle": "Sam K!", "passed": 1, "total": 2}).status_code == 400
    assert c.post("/api/eval", json={"room": "lab", "handle": "sam", "passed": 3, "total": 2}).status_code == 400
    placeholder = c.post("/api/register", json={"room": "lab", "handle": "your-handle", "url": "https://x.run.app",
                                                "flag_hashes": []})
    assert placeholder.status_code == 400 and "your-handle" in placeholder.json()["detail"]


def test_no_self_captures(monkeypatch):
    c = client(monkeypatch)
    c.post("/api/register", json={"room": "lab", "handle": "sam", "url": "https://x.run.app", "flag_hashes": [h("FLAG-aaaaaaaaaa")]})
    r = c.post("/api/capture", json={"room": "lab", "attacker": "sam", "target": "sam", "flag": "FLAG-aaaaaaaaaa"})
    assert r.status_code == 400


def vault_level(c, key="k1", points=3, admin="teach"):
    return c.post("/api/register", json={"room": "lab", "handle": "vault-1", "url": "https://vault.run.app",
                                         "app": "vault_1", "title": "Vault 1: Front office", "points": points,
                                         "verify_key": key, "admin": admin})


def test_only_instructors_register_the_vault(monkeypatch):
    c = client(monkeypatch)
    assert vault_level(c, admin="guess").status_code == 403
    sneaky = c.post("/api/register", json={"room": "lab", "handle": "vault-9", "url": "https://x.run.app", "flag_hashes": []})
    assert sneaky.status_code == 403
    assert vault_level(c).status_code == 200


def test_vault_codes_are_personal_and_score_for_everyone(monkeypatch):
    c = client(monkeypatch)
    vault_level(c)
    mod = sys.modules["main"]
    mei, kai = mod.vault_code("k1", "mei"), mod.vault_code("k1", "kai")
    assert mei != kai

    shared = c.post("/api/capture", json={"room": "lab", "attacker": "kai", "target": "vault-1", "flag": mei})
    assert shared.status_code == 400

    first = c.post("/api/capture", json={"room": "lab", "attacker": "mei", "target": "vault-1", "flag": mei.lower()})
    assert first.json()["message"] == "Capture confirmed: mei cracked Vault 1: Front office for 5 points. First in the room: +2 bonus."
    second = c.post("/api/capture", json={"room": "lab", "attacker": "kai", "target": "vault-1", "flag": " " + kai + " "})
    assert second.json()["message"] == "Capture confirmed: kai cracked Vault 1: Front office for 3 points."
    again = c.post("/api/capture", json={"room": "lab", "attacker": "kai", "target": "vault-1", "flag": kai})
    assert again.json()["message"] == "You already cracked this level."

    board = c.get("/api/board").json()
    assert {r["handle"]: r["points"] for r in board["attackers"]} == {"mei": 5, "kai": 3}
    assert board["vault"][0]["cracked"] == 2 and board["vault"][0]["first"] == "mei"
    assert board["targets"] == []
    assert "verify_key" not in str(board) and "k1" not in str(board)
    assert board["recent"][0]["vault"] is True


def test_vault_and_leaderboard_mint_the_same_codes(monkeypatch):
    client(monkeypatch)  # loads the leaderboard module
    sys.path.insert(0, str(ROOT / "vault"))
    try:
        import vaultlib
    finally:
        sys.path.pop(0)
    key = vaultlib.level_key(2)
    assert sys.modules["main"].vault_code(key, "mei") == vaultlib.mint(key, "mei")
