.PHONY: install dev-api dev-ui test lint data docker-up

install:            ## Install backend (venv) and frontend dependencies
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm ci

dev-api:            ## Run the API with auto-reload on :8000
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-ui:             ## Run the React dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

test:               ## Run all tests
	cd backend && .venv/bin/pytest -q
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run typecheck

data:               ## Download the January 2026 Elexon snapshot into backend/data
	cd backend && .venv/bin/python -m scripts.fetch_data

docker-up:          ## Build and run the production image on :8000
	docker compose up --build
