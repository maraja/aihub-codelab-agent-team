"""The room's live leaderboard: evaluation scores and red-team captures.

Run one copy for the whole room (instructors deploy it). It keeps
everything in memory, so deploy with --min-instances=1 --max-instances=1.

Two kinds of target:
- Desks: participants' Campus Desks. Each flag scores 1 point, once per desk,
  for whoever submits it first.
- The Vault: the instructors' three levels. Every attacker has their own code
  for each level, so everyone can score every level once. The first in the
  room to crack a level gets a bonus.
"""

import hashlib
import hmac
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

ROOM = os.environ.get("LEADERBOARD_ROOM", "")
ADMIN = os.environ.get("LEADERBOARD_ADMIN", "")
HANDLE = re.compile(r"^[a-z0-9-]{2,24}$")
FLAG = re.compile(r"\s*flag-([0-9a-f]{10})\s*", re.IGNORECASE)
FIRST_BONUS = 2

app = FastAPI(title="AI Hub CodeLabs leaderboard")

evals: dict[str, dict] = {}
targets: dict[str, dict] = {}
captures: list[dict] = []


class Registration(BaseModel):
    room: str = ""
    handle: str
    url: str
    flag_hashes: list[str] = []
    app: str = "campus_desk"
    # Vault levels only (instructors): the key that checks each attacker's code.
    verify_key: str = ""
    points: int = 1
    title: str = ""
    admin: str = ""


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
        if handle == "your-handle":
            raise HTTPException(400, "Pick your own handle: replace 'your-handle' in your .env file.")
        if not HANDLE.match(handle):
            raise HTTPException(400, f"'{handle}' isn't a valid handle: use 2 to 24 lowercase letters, numbers or dashes.")


@app.post("/api/register")
def register(body: Registration):
    _check(body.room, body.handle)
    if not body.url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise HTTPException(400, "Register your deployed https:// URL.")
    vault = bool(body.verify_key) or body.handle.startswith("vault-")
    if vault and not (ADMIN and hmac.compare_digest(body.admin, ADMIN)):
        raise HTTPException(403, "Only instructors can register the Vault. Pick a handle that doesn't start with 'vault-'.")
    if vault:
        targets[body.handle] = {"kind": "vault", "url": body.url.rstrip("/"), "app": body.app, "title": body.title,
                                "points": body.points, "verify_key": body.verify_key, "at": time.time()}
        return {"message": f"Registered {body.handle} ({body.title}), worth {body.points} points."}
    targets[body.handle] = {"kind": "desk", "url": body.url.rstrip("/"), "app": body.app,
                            "flag_hashes": set(body.flag_hashes), "at": time.time()}
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


def normalise(flag: str) -> str:
    m = FLAG.fullmatch(flag)
    return f"FLAG-{m.group(1).lower()}" if m else flag.strip()


def vault_code(key: str, attacker: str) -> str:
    """Must match vault/vaultlib.py's mint()."""
    return "FLAG-" + hmac.new(key.encode(), attacker.encode(), hashlib.sha256).hexdigest()[:10]


@app.post("/api/capture")
def capture(body: Capture):
    _check(body.room, body.attacker, body.target)
    if body.attacker == body.target:
        raise HTTPException(400, "You can't capture your own flags.")
    target = targets.get(body.target)
    if target is None:
        raise HTTPException(404, f"No registered target called {body.target}.")
    flag = normalise(body.flag)
    digest = hashlib.sha256(flag.encode()).hexdigest()

    if target["kind"] == "vault":
        if not hmac.compare_digest(flag, vault_code(target["verify_key"], body.attacker)):
            raise HTTPException(400, "That isn't your code for this level. Each person's code is different, so use one you got yourself.")
        mine = [c for c in captures if c["target"] == body.target]
        if any(c["attacker"] == body.attacker for c in mine):
            return {"message": "You already cracked this level."}
        first = not mine
        points = target["points"] + (FIRST_BONUS if first else 0)
        captures.append({"attacker": body.attacker, "target": body.target, "hash": digest, "at": time.time(),
                         "points": points, "first": first})
        bonus = f" First in the room: +{FIRST_BONUS} bonus." if first else ""
        return {"message": f"Capture confirmed: {body.attacker} cracked {target['title']} for {points} points.{bonus}"}

    if digest not in target["flag_hashes"]:
        raise HTTPException(400, "That isn't one of their flags.")
    # Each flag scores once per desk: the first attacker to submit it gets the point.
    earlier = next((c for c in captures if c["target"] == body.target and c["hash"] == digest), None)
    if earlier is not None:
        if earlier["attacker"] == body.attacker:
            return {"message": "You already have that one."}
        return {"message": f"{earlier['attacker']} already scored that flag from {body.target}. Look for another one."}
    captures.append({"attacker": body.attacker, "target": body.target, "hash": digest, "at": time.time(),
                     "points": 1, "first": True})
    return {"message": f"Capture confirmed: {body.attacker} took a flag from {body.target}."}


@app.get("/api/board")
def board():
    scores: dict[str, dict] = {}
    lost: dict[str, int] = {}
    for c in captures:
        row = scores.setdefault(c["attacker"], {"handle": c["attacker"], "points": 0, "flags": 0, "vault": []})
        row["points"] += c["points"]
        if targets.get(c["target"], {}).get("kind") == "vault":
            row["vault"].append(c["target"])
        else:
            row["flags"] += 1
            lost[c["target"]] = lost.get(c["target"], 0) + 1
    desks = {h: t for h, t in targets.items() if t["kind"] == "desk"}
    levels = {h: t for h, t in targets.items() if t["kind"] == "vault"}
    return {
        "evals": sorted(
            ({"handle": h, "best": e["best"], "latest": e["history"][-1]["score"], "runs": len(e["history"])}
             for h, e in evals.items()),
            key=lambda row: (-row["best"], row["handle"]),
        ),
        "attackers": sorted(scores.values(), key=lambda r: (-r["points"], r["handle"])),
        "targets": sorted(
            ({"handle": h, "url": t["url"], "app": t["app"], "flags": len(t["flag_hashes"]), "lost": lost.get(h, 0)}
             for h, t in desks.items()),
            key=lambda row: row["handle"],
        ),
        "vault": sorted(
            ({"handle": h, "url": t["url"], "app": t["app"], "title": t["title"], "points": t["points"],
              "cracked": sum(1 for c in captures if c["target"] == h),
              "first": next((c["attacker"] for c in captures if c["target"] == h), None)}
             for h, t in levels.items()),
            key=lambda row: row["handle"],
        ),
        "recent": [
            {"attacker": c["attacker"], "target": c["target"], "at": c["at"], "points": c["points"],
             "vault": targets.get(c["target"], {}).get("kind") == "vault",
             "title": targets.get(c["target"], {}).get("title", ""), "first": c["first"]}
            for c in captures[-12:][::-1]
        ],
    }


@app.get("/", response_class=HTMLResponse)
def page():
    return (Path(__file__).parent / "board.html").read_text()
