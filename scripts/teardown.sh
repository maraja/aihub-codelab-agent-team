#!/usr/bin/env bash
# Deletes what a deploy left in your project, so nothing keeps costing money:
# the Cloud Run services you name and their container images. Once nothing else
# is running in the region, it also deletes the container repository and the
# bucket that holds your uploaded source code.
#   ./scripts/teardown.sh campus-desk                        (make teardown)
#   ./scripts/teardown.sh codelab-leaderboard codelab-vault  (make leaderboard-down)
# Safe to run twice: anything already gone is skipped.
set -uo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
if [ "$PROJECT" = "your-project-id" ]; then
  echo "GOOGLE_CLOUD_PROJECT is still 'your-project-id'. Put your real project ID in .env (it overrides export)." >&2
  exit 1
fi
if [ "$#" -eq 0 ]; then
  echo "Name the services to delete, for example: ./scripts/teardown.sh campus-desk" >&2
  exit 1
fi
REGION="${CLOUD_RUN_REGION:-northamerica-northeast2}"
REPO="cloud-run-source-deploy"
BUCKET="gs://run-sources-$PROJECT-$REGION"
WHERE=(--project "$PROJECT" --region "$REGION")
FAILED=0

echo "Cleaning up in project $PROJECT, region $REGION."
for SERVICE in "$@"; do
  if gcloud run services describe "$SERVICE" "${WHERE[@]}" > /dev/null 2>&1; then
    if gcloud run services delete "$SERVICE" "${WHERE[@]}" --quiet; then
      echo "Deleted the service: $SERVICE"
    else
      FAILED=1
    fi
  else
    echo "No service called $SERVICE here. Already gone."
  fi
  if gcloud artifacts packages describe "$SERVICE" --repository "$REPO" --location "$REGION" --project "$PROJECT" > /dev/null 2>&1; then
    if gcloud artifacts packages delete "$SERVICE" --repository "$REPO" --location "$REGION" --project "$PROJECT" --quiet > /dev/null 2>&1; then
      echo "Deleted its container images: $SERVICE"
    else
      echo "Couldn't delete the container images for $SERVICE." >&2
      FAILED=1
    fi
  fi
done

# The repository and the source bucket are shared by everything deployed in this
# region, so they only go once nothing else is running here.
LEFT="$(gcloud run services list "${WHERE[@]}" --format='value(metadata.name)' 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')"
if [ -n "$LEFT" ]; then
  echo "Still running in $REGION: $LEFT. Kept the shared container repository and source bucket for them."
else
  if gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT" > /dev/null 2>&1; then
    if gcloud artifacts repositories delete "$REPO" --location "$REGION" --project "$PROJECT" --quiet > /dev/null 2>&1; then
      echo "Deleted the container repository."
    else
      echo "Couldn't delete the container repository $REPO." >&2
      FAILED=1
    fi
  fi
  if gcloud storage buckets describe "$BUCKET" --project "$PROJECT" > /dev/null 2>&1; then
    if gcloud storage rm --recursive "$BUCKET" --project "$PROJECT" --quiet > /dev/null 2>&1; then
      echo "Deleted the uploaded source code."
    else
      echo "Couldn't delete the source bucket $BUCKET." >&2
      FAILED=1
    fi
  fi
fi

echo
ALL="$(gcloud run services list --project "$PROJECT" --format='value(metadata.name,region)' 2>/dev/null)"
if [ -z "$ALL" ]; then
  echo "Nothing is running on Cloud Run in $PROJECT any more."
else
  echo "Still on Cloud Run in $PROJECT:"
  echo "$ALL" | sed 's/^/  /'
fi
exit "$FAILED"
