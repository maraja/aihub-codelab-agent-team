#!/usr/bin/env bash
# Instructors: deploy the room's leaderboard to Cloud Run (one copy per room),
# then the Vault, and put the Vault's three levels on the board.
#   make leaderboard                  # makes up a room code
#   make leaderboard ROOM=durham-nov  # or pick your own
#   make leaderboard VAULT=0          # the board without the Vault
#   make leaderboard-down             # delete both at the end of the day
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
if [ "$PROJECT" = "your-project-id" ]; then
  echo "GOOGLE_CLOUD_PROJECT is still 'your-project-id'. Put your real project ID in .env (it overrides export)." >&2
  exit 1
fi
REGION="${CLOUD_RUN_REGION:-northamerica-northeast2}"
SERVICE="codelab-leaderboard"

# The room code stops people outside the room posting to your board. It's
# read from ROOM, not LEADERBOARD_ROOM, because .env's example value would
# otherwise become the code. It's saved, so a redeploy keeps the same code
# (delete .leaderboard_room to get a new one for your next workshop).
ROOM="${ROOM:-$(cat .leaderboard_room 2>/dev/null || true)}"
if [ -z "$ROOM" ]; then
  ROOM="room-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
fi
echo "$ROOM" > .leaderboard_room

# The instructors' key: only it can put the Vault on the board. It stays in
# this folder and the service.
[ -f .leaderboard_admin ] || python3 -c "import secrets; print(secrets.token_hex(16))" > .leaderboard_admin

# Everything lives in memory, so exactly one instance, always on: a second
# instance would split the board, and a restart would wipe it.
gcloud run deploy "$SERVICE" \
  --source leaderboard \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=1 \
  --set-env-vars "LEADERBOARD_ROOM=$ROOM,LEADERBOARD_ADMIN=$(cat .leaderboard_admin)"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
cat <<MSG

The leaderboard is live. Put this on the big screen:
  $URL

Give the room these two lines for their .env:
  LEADERBOARD_URL=$URL
  LEADERBOARD_ROOM=$ROOM

It stays on (and keeps costing a little) until you run: make leaderboard-down
MSG

# Then the Vault, the instructors' three-level challenge for the red-team round.
if [ "${VAULT:-1}" != "0" ]; then
  echo
  echo "Now deploying the Vault (a few more minutes)..."
  if ! BOARD_URL="$URL" ROOM="$ROOM" ./scripts/vault.sh; then
    echo
    echo "The board is up, but the Vault isn't. Fix the error above, then run: make vault"
  fi
fi
