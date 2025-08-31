.PHONY: help setup-db ingest init-model update-model run-pipeline streamlit clean

help: ## Show this help message
	@echo "BERTopic CORE Online MVP - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup-db: ## Start PostgreSQL database with Docker Compose
	docker-compose up -d db
	@echo "Database started. Connection string: postgresql+psycopg2://coreuser:corepass@localhost:5432/coredb"

setup-db-manual: ## Setup database manually (if not using Docker)
	@echo "To setup database manually:"
	@echo "1. Install PostgreSQL"
	@echo "2. Create database: createdb coredb"
	@echo "3. Run schema: psql -d coredb -f db_schema.sql"

ingest: ## Ingest papers from CORE API (default: 2021-2025, limit 200)
	python ingest/core_ingest.py --from_year 2021 --to_year 2025 --lang en --limit 200

ingest-full: ## Ingest all papers from CORE API (2021-2025)
	python ingest/core_ingest.py --from_year 2021 --to_year 2025 --lang en

init-model: ## Initialize BERTopic model with existing data
	python pipelines/pipeline_online.py --mode init --batch_path data/clean/2021_2025_en.parquet

update-model: ## Update BERTopic model with new data
	python pipelines/pipeline_online.py --mode update --batch_path data/clean/2021_2025_en.parquet

run-pipeline: ## Run complete end-to-end pipeline
	python pipelines/run_end_to_end.py --from_year 2021 --to_year 2025 --lang en --limit 200 --init_if_missing

run-pipeline-full: ## Run complete pipeline without limits
	python pipelines/run_end_to_end.py --from_year 2021 --to_year 2025 --lang en --init_if_missing

run-pipeline-no-db: ## Run pipeline without database (for testing)
	python pipelines/run_end_to_end.py --from_year 2021 --to_year 2025 --lang en --limit 200 --init_if_missing --skip_db

streamlit: ## Start Streamlit dashboard
	streamlit run app/streamlit_app.py

test-smoke: ## Run smoke test with small dataset
	python pipelines/run_end_to_end.py --from_year 2021 --to_year 2022 --lang en --limit 100 --init_if_missing

clean: ## Clean generated files and data
	rm -rf data/raw/*.jsonl
	rm -rf data/clean/*.parquet
	rm -rf models/artifacts/*
	rm -rf models/checkpoints/*

clean-all: ## Clean everything including Docker volumes
	docker-compose down -v
	rm -rf data/raw/*.jsonl
	rm -rf data/clean/*.parquet
	rm -rf models/artifacts/*
	rm -rf models/checkpoints/*

install: ## Install dependencies
	pip install -r requirements.txt

env-setup: ## Setup environment variables
	@echo "Setting up environment variables..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	@echo "Please edit .env with your CORE_API_KEY and DATABASE_URL"

quick-start: ## Quick start with smoke test
	@echo "Quick start with smoke test..."
	@echo "1. Setting up environment..."
	$(MAKE) env-setup
	@echo "2. Starting database..."
	$(MAKE) setup-db
	@echo "3. Running smoke test..."
	$(MAKE) test-smoke
	@echo "4. Starting Streamlit dashboard..."
	$(MAKE) streamlit
