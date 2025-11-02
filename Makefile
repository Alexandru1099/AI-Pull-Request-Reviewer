.PHONY: help up down logs backend-uv backend-dev frontend-dev

help:
	@echo "Repo-Aware AI Pull Request Reviewer - Phase 1"
	@echo ""
	@echo "Targets:"
	@echo "  up           - Start frontend and backend via docker-compose"
	@echo "  down         - Stop all docker-compose services"
	@echo "  logs         - Tail logs from all services"
	@echo "  backend-uv   - Run backend locally with uvicorn"
	@echo "  backend-dev  - Run backend locally (using uv if present)"
	@echo "  frontend-dev - Run frontend locally (Next.js dev server)"

up:
	docker-compose up --build

down:
	docker-compose down

logs:
	docker-compose logs -f

backend-uv:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-dev:
	cd backend && \
	if command -v uv >/dev/null 2>&1; then \
		uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	fi

frontend-dev:
	cd frontend && yarn dev
