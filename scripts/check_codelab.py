"""Checks that every code block marked in the codelab matches the tested code.

    uv run python scripts/check_codelab.py path/to/en.md

A block marked <!-- check: 1-crew/campus_desk/agent.py --> must appear,
line for line, in that checkpoint file. For the crew agent.py, the
after_model_callback lines are ignored, since the codelab adds them in step 7.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"<!-- check: (\S+) -->\n```\w*\n(.*?)\n```", re.S)


def lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.strip("\n").splitlines()]


def contains(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


markdown = Path(sys.argv[1]).read_text()
failures = 0
blocks = BLOCK.findall(markdown)
for target, code in blocks:
    source = lines((ROOT / "checkpoints" / target).read_text())
    snippet = lines(code)
    without_review = [line for line in source if "after_model_callback=review_reply" not in line]
    if not (contains(source, snippet) or contains(without_review, snippet)):
        failures += 1
        print(f"MISMATCH in {target}:\n  " + "\n  ".join(snippet[:3]) + "\n  ...")
print(f"{len(blocks) - failures}/{len(blocks)} code blocks match the checkpoints.")
sys.exit(1 if failures else 0)
