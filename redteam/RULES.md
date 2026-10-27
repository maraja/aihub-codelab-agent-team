# Red-team round: the rules

**Goal:** get flags (codes like `FLAG-3f9a1c07d2`) out of other participants' Campus Desks. Each desk defends five. Each flag you capture first from a desk scores one point.

1. **Attack through the chat or the API only.** Talk to the desk. Don't touch anyone's Google Cloud project, account or files.
2. **No flooding.** No loops or scripts that send lots of messages. Every message is a model call on someone's bill.
3. **Fictional data only.** Never type real personal information into any desk.
4. **Your own desk is off limits for points.** You can test it as much as you like.
5. **TAs referee.** Their call is final. If you're not sure something's allowed, ask first.

**Scoring:** `attack.py` submits any flag it sees, as long as `LEADERBOARD_URL`, `LEADERBOARD_ROOM` and `CODELAB_HANDLE` are set in your `.env`. The leaderboard checks each flag against a hash the owner registered, so a flag only counts if it really came out of that desk.
