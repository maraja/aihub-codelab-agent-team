# AI Hub Codelab: Build, Break and Defend an AI Agent Team

You'll build the **Campus Desk**, a team of AI agents that runs a help desk for Ridgeview Polytechnic (a fictional college). Then you'll put it on the cloud, try to break other participants' desks, and defend your own.

The step-by-step lab lives on the AI Hub site. This repo has the code.

| Folder | What's in it |
|---|---|
| `starter/` | Where you work. Every step in the lab edits files in `starter/campus_desk`. |
| `checkpoints/1-crew/` | The finished team, before the red-team round. Copy from here if you fall behind. |
| `checkpoints/2-defended/` | The finished team after all three patches. |
| `evals/` | The test cases and the script that scores your desk. |
| `redteam/` | The attack tool and the rules for the red-team round. |
| `leaderboard/` | The room's scoreboard. Instructors run one copy. |
| `scripts/` | Project setup, deploy and leaderboard registration. |
| `tests/` | Offline tests of the lab's plumbing. They use a scripted stand-in for Gemini, so they cost nothing. |

## Quick start (in Cloud Shell)

```shell
export GOOGLE_CLOUD_PROJECT=your-project-id
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
make install      # Python packages
make setup        # Google Cloud services and permissions, once per project
cp .env.example .env   # then fill in your handle and the leaderboard details
make web          # chat with your desk on port 8000
make eval         # score it
make deploy       # ship it to Cloud Run
make teardown     # delete it at the end of the day
```

Everything in Ridgeview Polytechnic's data is made up: names, emails, phone numbers and policies.

## Versions

Checked on October 27, 2026:

- `google-adk==2.13.0` (Python 3.11 or newer)
- Model: `gemini-3.8-flash` through Gemini Enterprise Agent Platform's `global` endpoint (formerly Vertex AI). Change it with `CAMPUS_DESK_MODEL`.
- Cloud Run region: `northamerica-northeast2` (Toronto). Change it with `make deploy REGION=...`.
