# TaskMaster

TaskMaster is a modern web-based task management application built with Django and enhanced with HTMX for dynamic user interactions. It aims to provide an intuitive interface for managing personal and potentially team tasks efficiently.

## Features

* **Task Management:**
  * Create, view, update, and delete tasks.
  * Tasks include: title, description, status (To Do, In Progress, On Hold, Completed), priority (Low, Medium, High, None), due date & time, and scheduled date.
  * Timestamps for task creation and last modification.
* **User Interface:**
  * Clean, modern UI styled with Tailwind CSS .
  * Dynamic task list updates and form submissions powered by HTMX.
  * Dedicated page for adding new tasks.
  * Homepage/Tasks page displaying "Today" and "Upcoming" tasks.
  * Interactive elements like hover effects for task titles and delete icons.
* **User Authentication:**
  * Login page (foundation for user accounts).
  * Login with Google
* **Backend:**
  * Built with Django.
  * Service layer for encapsulating business logic (e.g., `task_add_service`, `task_delete_service`).
  * Custom exceptions for specific error handling (e.g., `DueDateInPastError`).
  * Admin interface for managing tasks.
  * django-allauth for handling social logins.
* **Development & Tooling:**
  * Environment variable management with `django-environ`.
  * Package management with `uv`.
  * Static type checking with `Pyright`.
  * Linting and formatting with `Ruff`.

## Tech Stack

* **Backend:** Python 3.13, Django
* **Frontend:** HTML, Tailwind CSS, HTMX, daisyUI
* **Database:** SQLite (default, support will be added to be configurable via `DATABASE_URL`)
* **Key Django Packages:**
  * `django-htmx`
  * `django-environ`
* **Development Tools:**
  * `uv` (Package manager)
  * `Pyright` (Static Type Checker)
  * `Ruff` (Linter & Formatter)

## Prerequisites

* Python 3.13+
* `uv` (Python package installer) - Can be installed with `pip install uv`

## Setup and Installation

1. **Clone the Repository (Example):**

    ```bash
    git clone https://github.com/andrew-anter/todo.git
    cd todo
    ```

2. **Create and Activate Virtual Environment (using `uv`):**

    ```bash
    uv venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate    # On Windows
    ```

3. **Install Dependencies (using `uv`):**
This command installs main dependencies and development tools specified in `pyproject.toml`.

    ```bash
    uv pip install -e ".[dev]"
    # Alternatively, if you prefer to sync exactly:
    # uv pip sync --all-extras
    ```

4. **Set Up Environment Variables:**
Create a `.env` file in the project root in the core directory (alongside `manage.py`). You can copy `.env.example` in core directory, or use the following template:

    ```env
    # .env

    # Django Settings
    SECRET_KEY=your_very_secret_django_key_here_please_change_me
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost

    # Database (default is SQLite in the project root)
    DATABASE_URL=sqlite:///db.sqlite3

    # Optional: If your Django settings module is not automatically found.
    # DJANGO_SETTINGS_MODULE=core.settings # Typically set by manage.py
    ```

    **Important:** Generate a new `SECRET_KEY` for your project.

5. **Run Database Migrations:**

    ```bash
    python manage.py makemigrations todo
    python manage.py migrate
    # Or using uv:
    # uv run python manage.py makemigrations todo
    # uv run python manage.py migrate
    ```

6. **Create a Superuser (Optional, for accessing the Django Admin):**

    ```bash
    python manage.py createsuperuser
    # Or using uv:
    # uv run python manage.py createsuperuser
    ```

    Follow the prompts to create an admin user.

7. **Run the Development Server:**

    ```bash
    python manage.py runserver
    # Or using uv:
    # uv run python manage.py runserver
    ```

    The application should now be running at `http://127.0.0.1:8000/`. The tasks page is likely at `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/tasks/` depending on your main `urls.py`.

8. For Running locally with an ssl for trying social logins:

```bash
uv run python manage.py runserver_plus --key-file selftest-key --cert-file selfteset-cert localhost:8443
```

## Development

### Running Linters and Type Checkers

* **Ruff (Check & Format):**

    ```bash
    uv run ruff check .
    uv run ruff format .
    ```

* **MyPy (Static Type Checking):**

    ```bash
    uv run pyright .
    ```
