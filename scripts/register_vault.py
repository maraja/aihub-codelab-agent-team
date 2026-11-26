"""Puts the Vault's three levels on the leaderboard (instructors only).

    uv run python scripts/register_vault.py <leaderboard-url> <vault-url> <room>

Needs VAULT_SEED and LEADERBOARD_ADMIN in the environment; scripts/vault.sh
sets both from .vault_seed and .leaderboard_admin.
"""

import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vault"))
from vaultlib import LEVELS, level_key  # noqa: E402

board, vault, room = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/"), sys.argv[3]
admin = os.environ.get("LEADERBOARD_ADMIN", "")
if not (os.environ.get("VAULT_SEED") and admin):
    sys.exit("VAULT_SEED and LEADERBOARD_ADMIN must be set. Run this through: make vault-register")

for level, info in LEVELS.items():
    try:
        r = httpx.post(f"{board}/api/register", timeout=30, json={
            "room": room, "handle": f"vault-{level}", "url": vault, "app": f"vault_{level}",
            "title": f"Vault {level}: {info['title']}", "points": info["points"],
            "verify_key": level_key(level), "admin": admin})
    except httpx.HTTPError as exc:
        sys.exit(f"Couldn't reach the leaderboard at {board} ({exc}).")
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    message = body.get("message") or body.get("detail") or r.text[:200]
    if r.status_code >= 400:
        sys.exit(f"The leaderboard refused vault-{level}: {message}")
    print(message)
