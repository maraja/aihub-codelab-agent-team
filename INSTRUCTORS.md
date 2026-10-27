# Running the day: instructors and TAs

## Before the day

- **Dry run.** Do the whole lab once in a fresh Google Cloud project with the real model, and time each block. The offline tests (`make test`) check the plumbing only, not how Gemini behaves.
- **Run the evals on both checkpoints** with the real model: `uv run python evals/run_evals.py checkpoints/1-crew` and `checkpoints/2-defended`. The crew version should fail several safety cases and the defended version should pass them. If a policy case fails on the defended version, adjust the case or the prompt before the day.
- **Send the setup checklist a week ahead:** create a project, turn on billing, open Cloud Shell. Billing needs a credit card, and that step takes the longest on the day.

## The leaderboard

Deploy one copy from an instructor's project:

```shell
gcloud run deploy codelab-leaderboard --source leaderboard \
  --region northamerica-northeast2 --allow-unauthenticated \
  --min-instances=1 --max-instances=1 \
  --set-env-vars LEADERBOARD_ROOM=pick-a-room-code
```

It keeps everything in memory, so it needs exactly one instance, always on, for the day. Put its URL on the big screen and give participants the URL and the room code.

## Refereeing the red-team round

- A capture only counts if the leaderboard confirms it, because it checks each flag against the owner's registered hashes. Disputes are about the rules, not the flags.
- Watch for flooding (a participant's desk slowing down, or one attacker with dozens of messages a minute).
- The usual first breaks, in the order people tend to find them: asking the booking agent to look up another student ID; reading the raw tool result even when the reviewer blocked the reply; asking for the staff override; the injected note on slot A-104.

## Common problems

| Symptom | Fix |
|---|---|
| `make deploy` fails with a permission error from Cloud Build | Run `make setup` again; it grants `roles/run.builder` to the compute service account. |
| The deployed desk answers with a 403 or "permission denied" from Agent Platform (Vertex AI) | The compute service account needs `roles/aiplatform.user`. `make setup` grants it. |
| Model not found | Check the model is available on the `global` endpoint, or set `CAMPUS_DESK_MODEL` to one that is. |
| "Session not found" against a deployed desk | The service scaled past one instance. The deploy script sets `--max-instances=1`; check it wasn't changed. |
| The desk won't start after Patch 1 | Expected until Patch 3 replaces `agent.py`. |

## At the end

Remind everyone to run `make teardown`. Then delete the leaderboard service.
