"""Tells the leaderboard where your Campus Desk lives and which flags it's defending.

Only hashes of your flags leave your laptop, so the leaderboard can check a
capture without ever knowing the flags.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from labenv import leaderboard_call, leaderboard_message, leaderboard_url, load_env  # noqa: E402
from harness import load_desk  # noqa: E402

load_env()

agent_dir, url = sys.argv[1], sys.argv[2]
handle = os.environ.get("CODELAB_HANDLE")
if not (leaderboard_url() and handle):
    sys.exit("Set LEADERBOARD_URL and CODELAB_HANDLE in .env first.")

desk = load_desk(agent_dir)
print(leaderboard_message(leaderboard_call("POST", "/api/register", json={
    "room": os.environ.get("LEADERBOARD_ROOM", ""), "handle": handle, "url": url,
    "flag_hashes": desk.flags.flag_hashes()})))
