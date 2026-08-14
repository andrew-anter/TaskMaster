.PHONY: run test lint format typecheck security deps css css-build css-watch \
        migrations migrate migrate-full shell check help

run: ## Run the development server
	uv run python manage.py runserver

test: ## Run the test suite
	uv run pytest

lint: ## Lint and fix issues with ruff
	uv run ruff check . --fix

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run basedpyright type checking
	uv run basedpyright .

security: ## Run bandit security checks
	uv run bandit -r . -x ./.venv

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
