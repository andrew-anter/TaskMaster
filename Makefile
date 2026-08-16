.PHONY: run dev test lint format typecheck security deps css css-build css-watch \
        migrations migrate migrate-full shell check worker beat worker-beat

dev: ## Run server + Celery worker/beat with eager tasks (full local dev)
	@trap 'kill 0' INT TERM; \
	CELERY_TASK_ALWAYS_EAGER=True CELERY_BROKER_URL=memory:// uv run python manage.py runserver & \
	CELERY_TASK_ALWAYS_EAGER=True CELERY_BROKER_URL=memory:// uv run celery -A core worker -B -l info & \
	wait

run: ## Run the development server
	uv run python manage.py runserver

worker: ## Run the Celery worker (requires a broker at CELERY_BROKER_URL)
	uv run celery -A core worker -l info

beat: ## Run the Celery beat scheduler (periodic tasks)
	uv run celery -A core beat -l info

worker-beat: ## Run worker + beat together (convenience for local dev)
	uv run celery -A core worker -B -l info

test: ## Run the test suite
	uv run pytest

lint: ## Lint and fix issues with ruff
	uv run ruff check . --fix

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run basedpyright type checking
	uv run basedpyright .

security: ## Run bandit security checks
	uv run bandit -r . -x ./.venv -c pyproject.toml

deps: ## Scan dependencies for vulnerabilities
	osv-scanner scan -r .

css-build: ## Build Tailwind CSS (production)
	./build-css.sh build

css-watch: ## Watch Tailwind CSS for changes
	./build-css.sh watch

css: css-build ## Build Tailwind CSS

migrations: ## Create new migrations after model changes
	uv run python manage.py makemigrations

migrate: ## Apply migrations
	uv run python manage.py migrate

migrate-full: migrations migrate ## Make and apply migrations

shell: ## Open the Django shell
	uv run python manage.py shell

check: lint format typecheck test ## Run all checks (lint, format, typecheck, test)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
