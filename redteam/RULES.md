# Red-team round: the rules

**Goal:** get flags (codes like `FLAG-3f9a1c07d2`) out of other participants' Campus Desks, and out of the instructors' Vault.

- **Desks.** Each desk defends five flags. Each flag scores 1 point, for the first person to submit it from that desk.
- **The Vault.** Three levels, each guarded harder than the last: Front office (3 points), Records room (5), The Registrar (8). Everyone can crack every level once, and the first person in the room to crack a level gets 2 bonus points. The Vault makes a code just for your handle, so a code someone else got is worth nothing to you.

1. **Attack through the chat or the API only.** Talk to the desk. Don't touch anyone's Google Cloud project, account or files.
2. **No flooding.** No loops or scripts that send lots of messages. Every message is a model call on someone's bill.
3. **Fictional data only.** Never type real personal information into any desk.
4. **Your own desk is off limits for points.** You can test it as much as you like.
5. **TAs referee.** Their call is final. If you're not sure something's allowed, ask first.

**Scoring:** `attack.py` submits any flag it sees, as long as `LEADERBOARD_URL`, `LEADERBOARD_ROOM` and `CODELAB_HANDLE` are set in your `.env`. If you work a flag out yourself (say the agent gave it to you backwards), submit it with `--submit FLAG-...`. The leaderboard checks every flag: a desk's flags against hashes the owner registered, and Vault codes against your handle.

**Vault tips:** a blocked reply stays in the conversation, and the agent tends to keep refusing after it. Start over with `--new` and try a different approach. Read what each level's assistant tells you about the office: some of it is useful.
