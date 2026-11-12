#!/usr/bin/env bash
# Instructors: deploy the room's leaderboard to Cloud Run (one copy per room).
#   make leaderboard                  # makes up a room code
#   make leaderboard ROOM=durham-nov  # or pick your own
#   make leaderboard-down             # delete it at the end of the day
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
# otherwise become the code.
ROOM="${ROOM:-}"
if [ -z "$ROOM" ]; then
  ROOM="room-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
fi

# Everything lives in memory, so exactly one instance, always on: a second
# instance would split the board, and a restart would wipe it.
gcloud run deploy "$SERVICE" \
  --source leaderboard \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=1 \
  --set-env-vars "LEADERBOARD_ROOM=$ROOM"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
cat <<EOF

The leaderboard is live. Put this on the big screen:
  $URL

Give the room these two lines for their .env:
  LEADERBOARD_URL=$URL
  LEADERBOARD_ROOM=$ROOM

It stays on (and keeps costing a little) until you run: make leaderboard-down
EOF
