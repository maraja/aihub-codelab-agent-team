#!/usr/bin/env bash
# Deploys your Campus Desk to Cloud Run and registers it on the leaderboard.
#   ./scripts/deploy.sh starter
# With REGISTER_ONLY=1 (make register) it skips the deploy and only registers.
set -euo pipefail

AGENT_DIR="${1:-starter}"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
if [ "$PROJECT" = "your-project-id" ]; then
  echo "GOOGLE_CLOUD_PROJECT is still 'your-project-id'. Put your real project ID in .env (it overrides export)." >&2
  exit 1
fi
REGION="${CLOUD_RUN_REGION:-northamerica-northeast2}"
SERVICE="campus-desk"

# Your flags come from this seed. Keep the file: redeploys reuse it.
SEED_FILE=".campus_desk_seed"
[ -f "$SEED_FILE" ] || python3 -c "import secrets; print(secrets.token_hex(16))" > "$SEED_FILE"
export CAMPUS_DESK_SEED="$(cat "$SEED_FILE")"

# Sessions live in memory, so one instance keeps each conversation in one place.
if [ -z "${REGISTER_ONLY:-}" ]; then
gcloud run deploy "$SERVICE" \
  --source "$AGENT_DIR" \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances=1 \
  --set-env-vars "CAMPUS_DESK_SEED=$CAMPUS_DESK_SEED,GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=global,CAMPUS_DESK_MODEL=${CAMPUS_DESK_MODEL:-gemini-3.8-flash}"
fi

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo
echo "Your Campus Desk is live: $URL/dev-ui/"

# Until your TA gives you the leaderboard's address, .env still has the example
# value, so there's nothing to register with yet.
LEADERBOARD="${LEADERBOARD_URL:-}"
if [ -z "$LEADERBOARD" ] || [ "$LEADERBOARD" = "https://the-url-your-ta-gives-you" ] \
   || [ -z "${CODELAB_HANDLE:-}" ] || [ "$CODELAB_HANDLE" = "your-handle" ]; then
  echo
  echo "Not on the leaderboard yet: put your handle and the leaderboard address in .env,"
  echo "then run: make register"
elif ! uv run python scripts/register.py "$AGENT_DIR" "$URL"; then
  echo
  echo "Your desk is live, but it isn't on the leaderboard yet."
  echo "Fix the line above in .env, then run: make register"
fi
