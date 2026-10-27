#!/usr/bin/env bash
# Deploys your Campus Desk to Cloud Run and registers it on the leaderboard.
#   ./scripts/deploy.sh starter
set -euo pipefail

AGENT_DIR="${1:-starter}"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
REGION="${CLOUD_RUN_REGION:-northamerica-northeast2}"
SERVICE="campus-desk"

# Your flags come from this seed. Keep the file: redeploys reuse it.
SEED_FILE=".campus_desk_seed"
[ -f "$SEED_FILE" ] || python3 -c "import secrets; print(secrets.token_hex(16))" > "$SEED_FILE"
export CAMPUS_DESK_SEED="$(cat "$SEED_FILE")"

# Sessions live in memory, so one instance keeps each conversation in one place.
gcloud run deploy "$SERVICE" \
  --source "$AGENT_DIR" \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances=1 \
  --set-env-vars "CAMPUS_DESK_SEED=$CAMPUS_DESK_SEED,GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=global,CAMPUS_DESK_MODEL=${CAMPUS_DESK_MODEL:-gemini-3.8-flash}"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo
echo "Your Campus Desk is live: $URL/dev-ui/"

if [ -n "${LEADERBOARD_URL:-}" ] && [ -n "${CODELAB_HANDLE:-}" ]; then
  uv run python scripts/register.py "$AGENT_DIR" "$URL"
fi
