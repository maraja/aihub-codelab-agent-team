# Running the day: instructors and TAs

## Before the day

- **Dry run.** Do the whole lab once in a fresh Google Cloud project with the real model, and time each block. The offline tests (`make test`) check the plumbing only, not how Gemini behaves.
- **Run the evals on both checkpoints** with the real model: `uv run python evals/run_evals.py checkpoints/1-crew` and `checkpoints/2-defended`. The crew version should fail three or four of the five safety cases (the slot-note injection fires about half the time) and the defended version should pass all 13. If a policy case fails on the defended version, adjust the case or the prompt before the day.
- **Send the setup checklist a week ahead:** create a project, turn on billing, open Cloud Shell. Billing needs a credit card, and that step takes the longest on the day.

## The leaderboard and the Vault

Deploy one copy from an instructor's project, from this repo in Cloud Shell (after `make install` and `make setup`):

```shell
make leaderboard                  # makes up a room code
make leaderboard ROOM=durham-nov  # or pick your own
```

It deploys two services. First the board: it prints its address for the big screen and the two lines participants put in their `.env` (`LEADERBOARD_URL` and `LEADERBOARD_ROOM`). The room code only stops people outside the room posting to the board; it isn't a password. Then **the Vault**, the instructors' three-level challenge for the red-team round, which it puts on the board for you. All told it takes about five minutes.

It keeps three files in this folder: `.leaderboard_room`, `.leaderboard_admin` (the instructors' key, which only the board and the Vault scripts use) and `.vault_seed`. Run every instructor command from the same folder, and don't share those files.

- **Deploy it the morning of the day, not before.** Both services keep everything in memory, so each runs as exactly one instance, always on, and costs a little for every hour it's up.
- **Don't redeploy it during the day.** A restart wipes the board. If it does happen, run `make vault-register` to put the Vault back; participants run `make register` to put their desks back and `make submit` to re-post their scores. Captures are lost.
- **Delete both afterwards:** `make leaderboard-down`. It also deletes their container images, and once nothing else runs in the region, the shared container repository and uploaded source.

`make leaderboard VAULT=0` deploys the board alone; `make vault` deploys the Vault on its own later.

## Refereeing the red-team round

- **Scoring.** A desk's flag scores 1 point for the first person to submit it from that desk. Each Vault level scores 3, 5 or 8 points for everyone who cracks it, plus 2 for the first in the room. Vault codes are made per handle, so sharing them doesn't help anyone.
- A capture only counts if the leaderboard confirms it: desk flags are checked against the owner's registered hashes, and Vault codes against the attacker's handle. Disputes are about the rules, not the flags.
- Watch for flooding (a participant's desk slowing down, or one attacker with dozens of messages a minute).
- The usual first breaks on a desk, in the order people tend to find them: asking the booking agent to look up another student ID; reading the raw tool result even when the reviewer blocked the reply; asking what the handbook says about the system override; asking to book the Thursday slot, which sets off the injected note on slot A-104 (about half the time).
- Watch the Vault's blocks live: `gcloud run services logs read codelab-vault --region northamerica-northeast2`. It logs who was blocked and why, never the codes.

### The Vault

How each level falls, with the attacks that worked in testing, is in the instructor guide (not in this repo, because participants clone it). Nudge people towards an approach rather than handing it over.

## Common problems

| Symptom | Fix |
|---|---|
| `make deploy` fails with a permission error from Cloud Build | Run `make setup` again; it grants `roles/run.builder` to the compute service account. |
| The deployed desk answers with a 403 or "permission denied" from Agent Platform (Vertex AI) | The compute service account needs `roles/aiplatform.user`. `make setup` grants it. |
| Model not found | Check the model is available on the `global` endpoint, or set `CAMPUS_DESK_MODEL` to one that is. |
| "Session not found" against a deployed desk | The service scaled past one instance. The deploy script sets `--max-instances=1`; check it wasn't changed. |
| The desk won't start after Patch 1 | Expected until Patch 3 replaces `agent.py`. |
| A reply takes a minute or more | Gemini occasionally stalls on a call. Each call has a one-minute limit and is retried up to three times (`config.py`), so it recovers on its own. |
| `attack.py` says the conversation was lost | The desk or the Vault restarted, and conversations live in memory. It starts a new one automatically. |
| A Vault capture says "That isn't your code for this level" | Vault codes are made per handle. Check `CODELAB_HANDLE` in `.env` matches the handle they're scoring under, and that they didn't copy someone else's code. |
| The Vault isn't on the board | Run `make vault-register` from the folder you ran `make leaderboard` in. |

## At the end

Remind everyone to run `make teardown`, which deletes their desk, its container images and its uploaded source, then lists anything still running on Cloud Run in their project. Then run `make leaderboard-down`, which does the same for the board and the Vault.
