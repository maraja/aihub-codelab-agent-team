"""Reads the lab's .env file, so every script sees your handle and leaderboard."""

import os
from pathlib import Path


def load_env() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


# The value .env.example ships with. Until a TA hands out the real address,
# treat it as "no leaderboard yet" instead of trying to reach it.
_PLACEHOLDER_LEADERBOARD = "https://the-url-your-ta-gives-you"


def leaderboard_url() -> str:
    """LEADERBOARD_URL without a trailing slash, or "" if it isn't set yet."""
    url = os.environ.get("LEADERBOARD_URL", "").strip().rstrip("/")
    return "" if url in ("", _PLACEHOLDER_LEADERBOARD) else url


def leaderboard_call(method: str, path: str, stop_on_error: bool = True, **kwargs) -> dict:
    """Calls the leaderboard and returns its JSON, or exits with a plain message.

    A refusal (wrong room, bad handle) also exits, unless stop_on_error is
    False, so the caller can report it and carry on.
    """
    import httpx

    url = leaderboard_url()
    if not url:
        raise SystemExit(
            "LEADERBOARD_URL isn't set yet. Put the address your TA gives you in .env."
        )
    try:
        response = httpx.request(method, f"{url}{path}", timeout=15, **kwargs)
    except httpx.HTTPError as exc:
        raise SystemExit(
            f"Couldn't reach the leaderboard at {url} ({exc}).\n"
            "Check LEADERBOARD_URL in .env against the address your TA gave you."
        )
    try:
        body = response.json()
    except ValueError:
        body = {"message": f"The leaderboard answered {response.status_code}: {response.text[:200]}"}
    if response.status_code >= 400 and stop_on_error:
        raise SystemExit(leaderboard_message(body))
    return body


def leaderboard_message(body: dict) -> str:
    return str(body.get("message") or body.get("detail") or body)
