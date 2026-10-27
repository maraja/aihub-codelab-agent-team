"""The room's live leaderboard: evaluation scores and red-team captures.

Run one copy for the whole room (instructors deploy it). It keeps
everything in memory, so deploy with --min-instances=1 --max-instances=1.
"""

import hashlib
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

ROOM = os.environ.get("LEADERBOARD_ROOM", "")
HANDLE = re.compile(r"^[a-z0-9-]{2,24}$")

app = FastAPI(title="AI Hub Codelab leaderboard")

evals: dict[str, dict] = {}
targets: dict[str, dict] = {}
captures: list[dict] = []


class Registration(BaseModel):
    room: str = ""
    handle: str
    url: str
    flag_hashes: list[str]


class EvalScore(BaseModel):
    room: str = ""
    handle: str
    passed: int
    total: int


class Capture(BaseModel):
    room: str = ""
    attacker: str
    target: str
    flag: str


def _check(room: str, *handles: str) -> None:
    if ROOM and room != ROOM:
        raise HTTPException(403, "Wrong room code. Check LEADERBOARD_ROOM.")
    for handle in handles:
        if not HANDLE.match(handle):
            raise HTTPException(400, f"'{handle}' isn't a valid handle: use 2 to 24 lowercase letters, numbers or dashes.")


@app.post("/api/register")
def register(body: Registration):
    _check(body.room, body.handle)
    if not body.url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise HTTPException(400, "Register your deployed https:// URL.")
    targets[body.handle] = {"url": body.url.rstrip("/"), "flag_hashes": set(body.flag_hashes), "at": time.time()}
    return {"message": f"Registered {body.handle}: {len(body.flag_hashes)} flags to defend at {body.url}"}


@app.post("/api/eval")
def submit_eval(body: EvalScore):
    _check(body.room, body.handle)
    if body.total <= 0 or not 0 <= body.passed <= body.total:
        raise HTTPException(400, "That score doesn't add up.")
    entry = evals.setdefault(body.handle, {"best": 0, "history": []})
    score = round(100 * body.passed / body.total)
    entry["history"].append({"score": score, "passed": body.passed, "total": body.total, "at": time.time()})
    entry["best"] = max(entry["best"], score)
    return {"message": f"Recorded {body.passed}/{body.total} ({score}%) for {body.handle}. Best so far: {entry['best']}%."}


@app.post("/api/capture")
def capture(body: Capture):
    _check(body.room, body.attacker, body.target)
    if body.attacker == body.target:
        raise HTTPException(400, "You can't capture your own flags.")
    target = targets.get(body.target)
    if target is None:
        raise HTTPException(404, f"No registered target called {body.target}.")
    digest = hashlib.sha256(body.flag.strip().encode()).hexdigest()
    if digest not in target["flag_hashes"]:
        raise HTTPException(400, "That isn't one of their flags.")
    if any(c["attacker"] == body.attacker and c["target"] == body.target and c["hash"] == digest for c in captures):
        return {"message": "You already have that one."}
    captures.append({"attacker": body.attacker, "target": body.target, "hash": digest, "at": time.time()})
    return {"message": f"Capture confirmed: {body.attacker} took a flag from {body.target}."}


@app.get("/api/board")
def board():
    points: dict[str, int] = {}
    lost: dict[str, int] = {}
    for c in captures:
        points[c["attacker"]] = points.get(c["attacker"], 0) + 1
        lost[c["target"]] = lost.get(c["target"], 0) + 1
    return {
        "evals": sorted(
            ({"handle": h, "best": e["best"], "latest": e["history"][-1]["score"], "runs": len(e["history"])}
             for h, e in evals.items()),
            key=lambda row: (-row["best"], row["handle"]),
        ),
        "attackers": sorted(({"handle": h, "points": p} for h, p in points.items()), key=lambda r: -r["points"]),
        "targets": sorted(
            ({"handle": h, "url": t["url"], "flags": len(t["flag_hashes"]), "lost": lost.get(h, 0)}
             for h, t in targets.items()),
            key=lambda row: row["handle"],
        ),
        "recent": [{"attacker": c["attacker"], "target": c["target"], "at": c["at"]} for c in captures[-10:][::-1]],
    }


@app.get("/", response_class=HTMLResponse)
def page():
    return (Path(__file__).parent / "board.html").read_text()
