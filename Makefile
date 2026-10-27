-include .env
export


# Which folder to run: your work in starter/, or a finished checkpoint.
AGENT_DIR ?= starter
REGION ?= northamerica-northeast2

.PHONY: setup install web eval submit deploy teardown test

setup:  ## One-time Google Cloud setup (APIs and permissions)
	./scripts/setup_project.sh

install:  ## Install everything the lab needs
	uv sync

web:  ## Chat with your agents in the browser (port 8000)
	uv run adk web $(AGENT_DIR) --port 8000

eval:  ## Score your agents against the test cases
	uv run python evals/run_evals.py $(AGENT_DIR)

submit:  ## Score your agents and post the score to the leaderboard
	uv run python evals/run_evals.py $(AGENT_DIR) --submit

deploy:  ## Deploy to Cloud Run and register on the leaderboard
	CLOUD_RUN_REGION=$(REGION) ./scripts/deploy.sh $(AGENT_DIR)

teardown:  ## Delete your Cloud Run service when the day is over
	gcloud run services delete campus-desk --region $(REGION) --quiet

test:  ## Offline tests of the lab's plumbing (no model calls)
	uv run pytest -q tests
