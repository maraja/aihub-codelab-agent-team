"""Scores your Campus Desk against the test cases in evals/cases.json.

    uv run python evals/run_evals.py starter
    uv run python evals/run_evals.py starter --only safety
    uv run python evals/run_evals.py starter --submit --handle your-name
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from labenv import load_env
from harness import check, load_desk, run_conversation

load_env()

CASES = Path(__file__).parent / "cases.json"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_dir", nargs="?", default="starter")
    parser.add_argument("--only", help="Run one category: policy, booking or safety.")
    parser.add_argument("--case", help="Run one case by its id.")
    parser.add_argument("--submit", action="store_true", help="Post your score to the leaderboard.")
    parser.add_argument("--handle", default=os.environ.get("CODELAB_HANDLE"))
    args = parser.parse_args()

    desk = load_desk(args.agent_dir)
    cases = json.loads(CASES.read_text())
    if args.only:
        cases = [c for c in cases if c["category"] == args.only]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]

    passed = 0
    for case in cases:
        try:
            transcript = await run_conversation(desk, case["turns"], approve=case.get("approve", False))
            problems = check(desk, case, transcript)
        except Exception as error:  # a crash is a failed case, not a stopped run
            problems = [f"crashed: {type(error).__name__}: {error}"]
        passed += not problems
        mark = "PASS" if not problems else "FAIL"
        print(f"{mark}  {case['category']:8} {case['id']}")
        for problem in problems:
            print(f"        - {problem}")

    total = len(cases)
    score = round(100 * passed / total) if total else 0
    print(f"\nScore: {passed}/{total} ({score}%)")

    if args.submit:
        if args.only or args.case:
            raise SystemExit("Only a full run counts for the leaderboard. Drop --only and --case to submit.")
        url = os.environ.get("LEADERBOARD_URL")
        if not (url and args.handle):
            raise SystemExit("Set LEADERBOARD_URL and --handle (or CODELAB_HANDLE) to submit.")
        response = httpx.post(
            f"{url.rstrip('/')}/api/eval",
            json={"room": os.environ.get("LEADERBOARD_ROOM", ""), "handle": args.handle,
                  "passed": passed, "total": total},
            timeout=15,
        )
        print(response.json().get("message", response.text))


if __name__ == "__main__":
    asyncio.run(main())
