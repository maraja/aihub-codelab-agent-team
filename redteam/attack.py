"""Talk to someone's deployed Campus Desk, or the Vault, and show everything it sends back.

    uv run python redteam/attack.py --list
    uv run python redteam/attack.py --target sam-k "Hi, what can you do?"
    uv run python redteam/attack.py --target sam-k "Tell me more"      (same conversation)
    uv run python redteam/attack.py --target sam-k --new "Start over"
    uv run python redteam/attack.py --target sam-k --approve yes      (answer an approval request)
    uv run python redteam/attack.py --target vault-1 "Hello"          (the instructors' Vault)
    uv run python redteam/attack.py --target vault-2 --submit FLAG-0123456789

Any flag it finds is submitted to the leaderboard for you. If you work a flag
out yourself (say the agent gave it to you backwards), submit it with --submit.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from labenv import leaderboard_call, leaderboard_message, leaderboard_url, load_env  # noqa: E402

load_env()

FLAG = re.compile(r"FLAG-[0-9a-f]{10}", re.IGNORECASE)
SESSIONS = Path(__file__).parent / ".sessions.json"
LEADERBOARD = leaderboard_url()
ROOM = os.environ.get("LEADERBOARD_ROOM", "")
BLOCKED_VAULT = "The Registrar's Office can't help with that."


def board() -> dict:
    if not LEADERBOARD:
        sys.exit("Set LEADERBOARD_URL first (your TA will give it to you).")
    return leaderboard_call("GET", "/api/board")


def resolve(target: str) -> dict:
    """A target is a handle on the leaderboard, a Vault level, or a full URL."""
    if target.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return {"url": target.rstrip("/"), "handle": "", "app": "campus_desk", "vault": False}
    b = board()
    for row in b["targets"]:
        if row["handle"] == target:
            return {"url": row["url"], "handle": target, "app": row.get("app", "campus_desk"), "vault": False}
    for row in b.get("vault", []):
        if row["handle"] == target:
            return {"url": row["url"], "handle": target, "app": row["app"], "vault": True}
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


def post(url: str, **kwargs) -> httpx.Response:
    try:
        return httpx.post(url, timeout=300, **kwargs)
    except httpx.TimeoutException:
        sys.exit("The agent took more than 5 minutes to answer. Try again, or try a shorter message.")
    except httpx.HTTPError as exc:
        sys.exit(f"Couldn't reach {url} ({exc}). Is that service still running?")


def new_session(url: str, app: str, user: str) -> dict:
    made = post(f"{url}/apps/{app}/users/{user}/sessions", json={})
    if made.status_code != 200:
        sys.exit(f"Couldn't start a conversation ({made.status_code}): {made.text[:300]}")
    return {"session_id": made.json()["id"], "pending": None}


def submit(target: dict, handle: str | None, flag: str) -> None:
    if LEADERBOARD and target["handle"] and handle:
        print("    " + leaderboard_message(leaderboard_call("POST", "/api/capture", stop_on_error=False, json={
            "room": ROOM, "attacker": handle, "target": target["handle"], "flag": flag})))
    else:
        print("    Set LEADERBOARD_URL and CODELAB_HANDLE, and use a handle as --target, to score it.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="?")
    parser.add_argument("--target", help="A handle from --list, a Vault level like vault-1, or a https:// URL.")
    parser.add_argument("--list", action="store_true", help="Show everyone you can attack.")
    parser.add_argument("--new", action="store_true", help="Start a fresh conversation.")
    parser.add_argument("--approve", choices=["yes", "no"], help="Answer the agent's approval request.")
    parser.add_argument("--submit", metavar="FLAG", help="Submit a flag you worked out yourself.")
    parser.add_argument("--handle", default=os.environ.get("CODELAB_HANDLE"), help="Your handle.")
    args = parser.parse_args()
    if args.handle == "your-handle":
        args.handle = None

    if args.list:
        b = board()
        for row in b["targets"]:
            print(f"{row['handle']:24} lost {row['lost']} of {row['flags']} flags   {row['url']}")
        for row in b.get("vault", []):
            print(f"{row['handle']:24} {row['title']} ({row['points']} points), cracked by {row['cracked']}")
        return
    if not args.target or not (args.message or args.approve or args.submit):
        parser.error("give --target and a message (or --approve yes/no, or --submit FLAG)")

    target = resolve(args.target)
    if args.submit:
        if not FLAG.fullmatch(args.submit.strip()):
            sys.exit("A flag looks like FLAG- followed by 10 characters from 0-9 and a-f.")
        print(f"*** Submitting {args.submit.strip()}")
        submit(target, args.handle, args.submit.strip())
        return
    if target["vault"] and not args.handle:
        sys.exit("Set CODELAB_HANDLE in .env first: the Vault makes a code just for your handle.")

    url, app = target["url"], target["app"]
    key = url if app == "campus_desk" else f"{url}#{app}"
    sessions = json.loads(SESSIONS.read_text()) if SESSIONS.exists() else {}
    user = f"redteam-{args.handle or 'anon'}"
    saved = sessions.get(key)
    if args.new or not saved:
        saved = new_session(url, app, user)

    if args.approve:
        if not saved.get("pending"):
            sys.exit("There's no approval request waiting in this conversation.")
        message = {"role": "user", "parts": [{"functionResponse": {
            "id": saved["pending"], "name": "adk_request_confirmation",
            "response": {"confirmed": args.approve == "yes"}}}]}
    else:
        message = {"role": "user", "parts": [{"text": args.message}]}

    def run() -> httpx.Response:
        return post(f"{url}/run", json={"app_name": app, "user_id": user, "session_id": saved["session_id"],
                                        "new_message": message})

    response = run()
    if response.status_code == 404 and "session" in response.text.lower() and not args.approve:
        # The service restarted, and conversations live in its memory.
        print("(That conversation was lost when the service restarted, so this is a new one.)\n")
        saved = new_session(url, app, user)
        response = run()
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
                found |= {"FLAG-" + f[5:].lower() for f in FLAG.findall(text)}
                if target["vault"] and text.strip() == BLOCKED_VAULT:
                    print(">>> A guard blocked that reply. Blocked replies stay in the conversation,"
                          " so try --new with a different approach.\n")
            call = part.get("functionCall") or part.get("function_call") or {}
            if call.get("name") == "adk_request_confirmation":
                saved["pending"] = call.get("id")
                print(">>> The agent wants approval. Answer with --approve yes or --approve no.\n")
    sessions[key] = saved
    SESSIONS.write_text(json.dumps(sessions, indent=2))

    for flag in sorted(found):
        print(f"*** Found {flag}")
        submit(target, args.handle, flag)


if __name__ == "__main__":
    main()
