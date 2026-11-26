-include .env
export


# Which folder to run: your work in starter/, or a finished checkpoint.
AGENT_DIR ?= starter
REGION ?= northamerica-northeast2
# Delete in the same project the deploy scripts use, not gcloud's default.
PROJECT_FLAG = $(if $(GOOGLE_CLOUD_PROJECT),--project $(GOOGLE_CLOUD_PROJECT))

.PHONY: setup install web eval submit deploy register teardown leaderboard leaderboard-down vault vault-register test

setup:  ## One-time Google Cloud setup (APIs and permissions)
	./scripts/setup_project.sh

install:  ## Install everything the lab needs
	uv sync

# Cloud Shell's Web Preview serves the page from *.cloudshell.dev. ADK 2.13
# blocks requests from any origin that isn't localhost unless it's listed,
# so without this the UI's scripts come back 403 and the page stays blank.
WEB_ORIGINS ?= regex:https://[a-z0-9.-]+\.cloudshell\.dev

web:  ## Chat with your agents in the browser (port 8000)
	uv run adk web $(AGENT_DIR) --port 8000 --allow_origins '$(WEB_ORIGINS)'

eval:  ## Score your agents against the test cases
	uv run python evals/run_evals.py $(AGENT_DIR)

submit:  ## Score your agents and post the score to the leaderboard
	uv run python evals/run_evals.py $(AGENT_DIR) --submit

deploy:  ## Deploy to Cloud Run and register on the leaderboard
	CLOUD_RUN_REGION=$(REGION) ./scripts/deploy.sh $(AGENT_DIR)

register:  ## Register your deployed desk on the leaderboard (no redeploy)
	REGISTER_ONLY=1 CLOUD_RUN_REGION=$(REGION) ./scripts/deploy.sh $(AGENT_DIR)

teardown:  ## Delete your Cloud Run service when the day is over
	gcloud run services delete campus-desk --region $(REGION) $(PROJECT_FLAG) --quiet

leaderboard:  ## Instructors: deploy the room's leaderboard and the Vault (ROOM=... to pick the code)
	CLOUD_RUN_REGION=$(REGION) ./scripts/leaderboard.sh

leaderboard-down:  ## Instructors: delete the leaderboard and the Vault at the end of the day
	gcloud run services delete codelab-leaderboard --region $(REGION) $(PROJECT_FLAG) --quiet
	-gcloud run services delete codelab-vault --region $(REGION) $(PROJECT_FLAG) --quiet

vault:  ## Instructors: deploy the Vault on its own and put it on the leaderboard
	CLOUD_RUN_REGION=$(REGION) ./scripts/vault.sh

vault-register:  ## Instructors: put the Vault back on the leaderboard (no redeploy)
	REGISTER_ONLY=1 CLOUD_RUN_REGION=$(REGION) ./scripts/vault.sh

test:  ## Offline tests of the lab's plumbing (no model calls)
	uv run pytest -q tests
