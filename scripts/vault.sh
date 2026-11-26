#!/usr/bin/env bash
# Instructors: deploy the Vault (the three-level challenge) and put it on the leaderboard.
# make leaderboard runs this for you. On its own:
#   make vault            # deploy and register
#   make vault-register   # register again, say after the leaderboard restarted
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
if [ "$PROJECT" = "your-project-id" ]; then
  echo "GOOGLE_CLOUD_PROJECT is still 'your-project-id'. Put your real project ID in .env (it overrides export)." >&2
  exit 1
fi
REGION="${CLOUD_RUN_REGION:-northamerica-northeast2}"
SERVICE="codelab-vault"

# Every attacker's codes come from this seed. Keep the file: redeploys reuse it.
[ -f .vault_seed ] || python3 -c "import secrets; print(secrets.token_hex(16))" > .vault_seed
export VAULT_SEED="$(cat .vault_seed)"

if [ -z "${REGISTER_ONLY:-}" ]; then
# Conversations live in memory, so one instance, always on.
gcloud run deploy "$SERVICE" \
  --source vault \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=1 \
  --set-env-vars "VAULT_SEED=$VAULT_SEED,GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=global,CAMPUS_DESK_MODEL=${CAMPUS_DESK_MODEL:-gemini-3.8-flash}"
fi

VAULT_URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
BOARD_URL="${BOARD_URL:-$(gcloud run services describe codelab-leaderboard --project "$PROJECT" --region "$REGION" --format='value(status.url)' 2>/dev/null || true)}"
ROOM="${ROOM:-$(cat .leaderboard_room 2>/dev/null || true)}"
if [ -z "$BOARD_URL" ] || [ ! -f .leaderboard_admin ]; then
  echo "The Vault is live at $VAULT_URL, but there's no leaderboard to register it with." >&2
  echo "Run make leaderboard from this folder first." >&2
  exit 1
fi
LEADERBOARD_ADMIN="$(cat .leaderboard_admin)" uv run python scripts/register_vault.py "$BOARD_URL" "$VAULT_URL" "$ROOM"
echo
echo "The Vault is live and on the leaderboard. Participants attack it with:"
echo "  uv run python redteam/attack.py --target vault-1 \"Hello\""
