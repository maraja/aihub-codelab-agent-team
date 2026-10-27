"""Talk to someone's deployed Campus Desk and show everything it sends back.

    uv run python redteam/attack.py --list
    uv run python redteam/attack.py --target sam-k "Hi, what can you do?"
    uv run python redteam/attack.py --target sam-k "Tell me more"      (same conversation)
    uv run python redteam/attack.py --target sam-k --new "Start over"
    uv run python redteam/attack.py --target sam-k --approve yes      (answer an approval request)

Any flag it finds is submitted to the leaderboard for you.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from labenv import load_env  # noqa: E402

load_env()

APP = "campus_desk"
FLAG = re.compile(r"FLAG-[0-9a-f]{10}")
SESSIONS = Path(__file__).parent / ".sessions.json"
LEADERBOARD = os.environ.get("LEADERBOARD_URL", "").rstrip("/")
ROOM = os.environ.get("LEADERBOARD_ROOM", "")


def board() -> dict:
    if not LEADERBOARD:
        sys.exit("Set LEADERBOARD_URL first (your TA will give it to you).")
    return httpx.get(f"{LEADERBOARD}/api/board", timeout=15).json()


def resolve(target: str) -> tuple[str, str]:
    """A target is a handle on the leaderboard or a full https:// URL."""
    if target.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return target.rstrip("/"), ""
    for row in board()["targets"]:
        if row["handle"] == target:
            return row["url"], target
    sys.exit(f"No target called {target}. Run with --list to see who's registered.")


def part_of(part: dict) -> tuple[str, str] | None:
    if part.get("text") and not part.get("thought"):
        return "says", part["text"]
    call = part.get("functionCall") or part.get("function_call")
    if call:
        return "calls tool", f"{call.get('name')}({json.dumps(call.get('args', {}))})"
    resp = part.get("functionResponse") or part.get("function_response")
    if resp:
        return "tool result", f"{resp.get('name')} -> {json.dumps(resp.get('response'))}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="?")
    parser.add_argument("--target", help="A handle from --list, or a https:// URL.")
    parser.add_argument("--list", action="store_true", help="Show everyone you can attack.")
    parser.add_argument("--new", action="store_true", help="Start a fresh conversation.")
    parser.add_argument("--approve", choices=["yes", "no"], help="Answer the agent's approval request.")
    parser.add_argument("--handle", default=os.environ.get("CODELAB_HANDLE"), help="Your handle.")
    args = parser.parse_args()

    if args.list:
        for row in board()["targets"]:
            print(f"{row['handle']:24} lost {row['lost']} of {row['flags']} flags   {row['url']}")
        return
    if not args.target or not (args.message or args.approve):
        parser.error("give --target and a message (or --approve yes/no)")

    url, target_handle = resolve(args.target)
    sessions = json.loads(SESSIONS.read_text()) if SESSIONS.exists() else {}
    user = f"redteam-{args.handle or 'anon'}"
    saved = sessions.get(url)
    if args.new or not saved:
        made = httpx.post(f"{url}/apps/{APP}/users/{user}/sessions", json={}, timeout=30)
        made.raise_for_status()
        saved = {"session_id": made.json()["id"], "pending": None}

    if args.approve:
        if not saved.get("pending"):
            sys.exit("There's no approval request waiting in this conversation.")
        message = {"role": "user", "parts": [{"functionResponse": {
            "id": saved["pending"], "name": "adk_request_confirmation",
            "response": {"confirmed": args.approve == "yes"}}}]}
    else:
        message = {"role": "user", "parts": [{"text": args.message}]}

    response = httpx.post(
        f"{url}/run",
        json={"app_name": APP, "user_id": user, "session_id": saved["session_id"], "new_message": message},
        timeout=120,
    )
    if response.status_code != 200:
        sys.exit(f"The agent returned {response.status_code}: {response.text[:300]}")

    saved["pending"] = None
    found = set()
    for event in response.json():
        for part in (event.get("content") or {}).get("parts", []):
            shown = part_of(part)
            if shown:
                kind, text = shown
                print(f"[{event.get('author')}] {kind}: {text}\n")
                found |= set(FLAG.findall(text))
            call = part.get("functionCall") or part.get("function_call") or {}
            if call.get("name") == "adk_request_confirmation":
                saved["pending"] = call.get("id")
                print(">>> The agent wants approval. Answer with --approve yes or --approve no.\n")
    sessions[url] = saved
    SESSIONS.write_text(json.dumps(sessions, indent=2))

    for flag in sorted(found):
        print(f"*** Found {flag}")
        if LEADERBOARD and target_handle and args.handle:
            result = httpx.post(f"{LEADERBOARD}/api/capture", timeout=15, json={
                "room": ROOM, "attacker": args.handle, "target": target_handle, "flag": flag})
            print("    " + result.json().get("message", result.json().get("detail", "")))
        else:
            print("    Set LEADERBOARD_URL and CODELAB_HANDLE, and use a handle as --target, to score it.")


if __name__ == "__main__":
    main()
