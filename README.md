# TaskMaster

A production-grade implementation of a decoupled Django web application demonstrating strict Separation of Concerns, advanced architecture patterns, and uncompromising software craftsmanship.
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=andrew-anter_todo&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=andrew-anter_todo)


## 🏗️ Architectural Highlights
- **Service/Selector Pattern:** Business logic encapsulated in services (`services.py`) with `@transaction.atomic`, queries in selectors (`selectors.py`). Views orchestrate but don't contain logic.
- **Custom Domain Exceptions:** Type-safe error handling with exceptions like `DueDateInPastError`, `ScheduledDateInPastError`.
- **Modern Tooling & Typing:** Utilizes `uv` for package management, `Ruff` for linting/formatting, `BasedPyright` for strict type checking, `bandit` for security analysis, and `osv-scanner` for dependency vulnerability scanning.
- **Dynamic Frontend Integration:** Leverages HTMX for high-performance partial page updates with Alpine.js for client-side interactivity.
- **REST API:** Full CRUD API at `/tasks/api/v1/` using Django REST Framework.

## 🛠️ Tech Stack & Tooling
- **Backend:** Python 3.13+, Django 5.2+, SQLite (Development) / PostgreSQL (Production ready)
- **Frontend:** HTMX, Tailwind CSS v4, daisyUI, Alpine.js
- **Admin:** django-unfold for modern admin interface
- **Quality Guardrails:** BasedPyright, Ruff, bandit, osv-scanner, pytest

## Features

* **Task Management:**
  * Create, view, update, and delete tasks.
  * Tasks include: title, description, status (To Do, In Progress, On Hold, Completed), priority (Low, Medium, High, None), due date & time, and scheduled date.
  * Timestamps for task creation and last modification.
* **Label System:**
  * Create and manage custom labels with colors.
  * Associate multiple labels with tasks.
  * Filter tasks by label.
* **User Interface:**
  * Clean, modern UI styled with Tailwind CSS and daisyUI.
  * Dynamic task list updates and form submissions powered by HTMX.
  * Dedicated page for adding new tasks.
  * Homepage/Tasks page displaying "Today" and "Upcoming" tasks.
  * Interactive elements like hover effects for task titles and delete icons.
* **User Authentication:**
  * Login/Register with username and password.
  * Login with Google (via django-allauth).
* **Backend:**
  * Built with Django using Service/Selector pattern.
  * Service layer for encapsulating business logic (e.g., `task_add_service`, `task_delete_service`).
  * Selector layer for permission-checked queries (e.g., `get_task_for_user`).
  * Custom exceptions for specific error handling.
  * Modern admin interface with django-unfold.
  * REST API with Django REST Framework.
* **Development & Tooling:**
  * Environment variable management with `django-environ`.
  * Package management with `uv`.
  * Static type checking with `BasedPyright`.
  * Linting and formatting with `Ruff`.
  * Security checks with `bandit`.
  * Dependency vulnerability scanning with `osv-scanner`.
  * Testing with `pytest` and `pytest-django`.

## Tech Stack

* **Backend:** Python 3.13+, Django 5.2+
* **Frontend:** HTML, Tailwind CSS v4, HTMX, daisyUI, Alpine.js
* **Database:** SQLite (default, configurable via `DATABASE_URL`)
* **Key Django Packages:**
  * `django-htmx` - HTMX integration
  * `django-environ` - Environment variable management
  * `django-allauth` - Authentication and social logins
  * `django-unfold` - Modern admin interface
  * `djangorestframework` - REST API
  * `django-colorfield` - Color picker for labels
* **Development Tools:**
  * `uv` (Package manager)
  * `BasedPyright` (Static Type Checker)
  * `Ruff` (Linter & Formatter)
  * `bandit` (Security Checker)
  * `osv-scanner` (Dependency Vulnerability Scanner)
  * `pytest` (Testing Framework)

## Prerequisites

* Python 3.13+
* `uv` (Python package installer) - Can be installed with `pip install uv`

## Setup and Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/andrew-anter/todo.git
    cd todo
    ```

2. **Create Virtual Environment and Install Dependencies:**

    ```bash
    uv sync
    ```

3. **Set Up Environment Variables:**
Create a `.env` file in the `core/` directory. You can copy `.env.example`:

    ```bash
    cp core/.env.example core/.env
    ```

    Edit `core/.env` and set your `SECRET_KEY` to a secure random value.

4. **Run Database Migrations:**

    ```bash
    uv run python manage.py migrate
    ```

5. **Create a Superuser (Optional, for accessing the Django Admin):**

    ```bash
    uv run python manage.py createsuperuser
    ```

6. **Run the Development Server:**

    ```bash
    uv run python manage.py runserver
    ```

    The application should now be running at `http://127.0.0.1:8000/`.

7. **Running with SSL (for social logins):**

    ```bash
    uv run python manage.py runserver_plus --key-file selftest-key --cert-file selftest-cert localhost:8443
    ```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

* **Linting & Formatting (Ruff):**

    ```bash
    uv run ruff check . --fix
    uv run ruff format .
    ```

* **Type Checking (BasedPyright):**

    ```bash
    uv run basedpyright .
    ```

* **Security Checks (bandit):**

    ```bash
    uv run bandit -r . -x ./.venv
    ```

* **Dependency Vulnerability Scanning (osv-scanner):**

    ```bash
    osv-scanner scan -r .
    ```

### Building Frontend Assets

After making changes to templates or forms, rebuild Tailwind CSS:

```bash
tailwindcss -i src/input.css -o static/css/output.css --minify
```
