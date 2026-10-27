#!/usr/bin/env bash
# One-time setup for your Google Cloud project: turns on the services the lab
# uses and lets Cloud Run build your code and call Gemini.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
gcloud config set project "$PROJECT"

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
RUNTIME="serviceAccount:${NUMBER}-compute@developer.gserviceaccount.com"
for ROLE in roles/run.builder roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="$RUNTIME" --role="$ROLE" --condition=None --quiet > /dev/null
done

echo "Project $PROJECT is ready."
