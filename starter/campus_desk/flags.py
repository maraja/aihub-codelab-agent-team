"""Secret flags for the red-team round.

Every deployment gets its own flags, made from a secret seed, so nobody can
read them from the repo. If an attacker gets one of your flags out of your
agent, they can prove it on the leaderboard.
"""

import hashlib
import hmac
import os
import re

FLAG_PATTERN = re.compile(r"FLAG-[0-9a-f]{10}")
_PLACEHOLDER = re.compile(r"\{flag:([a-zA-Z0-9-]+)\}")


def _seed() -> bytes:
    return os.environ.get("CAMPUS_DESK_SEED", "local-dev").encode()


def flag(name: str) -> str:
    digest = hmac.new(_seed(), name.encode(), hashlib.sha256).hexdigest()
    return f"FLAG-{digest[:10]}"


def fill_flags(text: str) -> str:
    """Replace {flag:name} placeholders in the data files with real flags."""
    return _PLACEHOLDER.sub(lambda m: flag(m.group(1)), text)


def flag_names() -> list[str]:
    from . import store

    return sorted(set(_PLACEHOLDER.findall(store.raw_data())))


def flag_hashes() -> list[str]:
    """What the leaderboard stores: hashes, so it never holds the flags."""
    return [hashlib.sha256(flag(n).encode()).hexdigest() for n in flag_names()]
