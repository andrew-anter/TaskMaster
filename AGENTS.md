# AGENTS.md

## Commands

```bash
# Development server
uv run python manage.py runserver

# Seed demo data (100 users, 50 labels, 100k tasks, notifications; --flush to reset)
uv run python manage.py seed_data
uv run python manage.py seed_data --users 50 --labels 20 --tasks 50000 --seed 42
uv run python manage.py seed_data --flush

# Celery worker / beat (task reminders)
make worker
make beat
make worker-beat   # combined, for local dev

# Tests
uv run pytest
uv run pytest tasks/tests/services_tests.py::TestAddTaskService::test_create_task_with_valid_data

# Linting & formatting
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run basedpyright .

# Security checks
uv run bandit -r . -x ./.venv -c pyproject.toml

# Dependency vulnerability checks
osv-scanner scan -r .

# Build Tailwind CSS (required after template changes)
./build-css.sh build
./build-css.sh watch  # for development with auto-rebuild
```

## Architecture

**Service/Selector pattern**: Business logic lives in `services.py` (write operations with `@transaction.atomic`), queries in `selectors.py` (read operations). Views orchestrate but don't contain logic.

**HTMX partials**: Views check `request.htmx` to return partial templates for dynamic updates vs full pages. Partials live in `templates/*/partials/`.

**Environment**: `.env` file goes in `core/` (not root). Settings loaded via `django-environ`.

**Custom user model**: `accounts.User` (extends `AbstractUser`). Reference via `settings.AUTH_USER_MODEL`.

**Apps**:
- `tasks`: Core task management (models, services, selectors, API)
- `labels`: Task labeling system
- `accounts`: Authentication (login/register/logout)
- `notifications`: **Generic notification subsystem** (model, `notify()`/`notify_bulk()` emitter API, UI). Other apps emit notifications by calling these services and registering type metadata.
- `common`: Shared middleware (`HtmxVaryMiddleware`), shared HTTP helpers (`hx_location_response`)

## Key Patterns

**Service functions** use keyword-only arguments and raise domain exceptions (`DueDateInPastError`, `ScheduledDateInPastError`):
```python
@transaction.atomic
def task_add_service(*, title: str, owner: User, ...) -> Task:
    if due_datetime and due_datetime.date() < today:
        raise DueDateInPastError(...)
```

**Selectors** are permission-checked query functions:
```python
def get_task_for_user(*, user: User, task_id: int) -> Task:
    return Task.objects.get(pk=task_id, owner=user)
```

**Views** handle HTMX vs standard requests:
```python
if request.htmx and not request.htmx.boosted:
    return render(request, "todo/partials/_task_list.html", context)
return render(request, "todo/task_list.html", context)
```

**Notifications**: Emit via `notifications.services.notify()` / `notify_bulk()`. Register per-type display metadata (`icon`, `label`) in `apps.py ready()` via `notifications.types.register_type`. Pass `dedupe_key` for idempotency. Periodic producers are Celery tasks (e.g. `tasks/tasks.py`); UI lives in `templates/notifications/`.

Notification behavior to preserve when modifying this subsystem:
- Read state is tracked solely by `read_at` (`services.py`): `read_at` is set to `now()` when a notification is marked read and stays `NULL` while unread. There is no `is_read` boolean.
- The unread badge count is cached per-user on the dedicated `notifications` cache alias (`core/settings.py` → `CACHES["notifications"]`). `notifications/selectors.py:get_unread_notifications_count` reads/writes it; any code path that creates or deletes notifications must call `invalidate_unread_notifications_count()`.
- Retention cleanup: `notifications/tasks.py:cleanup_old_notifications` (beat, daily) deletes read notifications older than `NOTIFICATIONS_READ_RETENTION_DAYS` (default 30) and unread ones older than `NOTIFICATIONS_UNREAD_RETENTION_DAYS` (default 90).
- GFK cascade: notifications targeting a deleted object are cascade-deleted via `notifications.signals.register_notification_cascade(model)` — register any new target model from its app's `apps.py ready()` (as `tasks/apps.py` does for `Task`).

## Testing

- Fixtures in `conftest.py` files per app
- Use `@pytest.mark.django_db` for database tests
- Test services directly, not views
- Fixtures chain: `valid_task_data` → `task_for_testing`

## Frontend

- **Tailwind CSS v4** with daisyUI plugin
- Input: `src/input.css` → Output: `static/css/output.css`
- Sources scanned: `templates/**`, `**/forms.py`
- Custom theme: `customBumblebee` (defined in `src/input.css`)
- Alpine.js for client-side interactivity

## Type Checking

- `basedpyright` in standard mode
- Excludes: `migrations/*.py`, `.venv/`, `__pycache__/`
- Stubs in `./typings/` (gitignored)
- Use `django_stubs_ext.monkeypatch()` (auto-enabled in DEBUG mode)

## Migrations

After model changes:
```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## API

REST API at `/tasks/api/v1/` using DRF. Endpoints in `tasks/api.py`. Authentication: Session + Basic.
