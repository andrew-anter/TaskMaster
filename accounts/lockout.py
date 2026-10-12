from django.core.cache import cache
from django.http import HttpRequest

LOCKOUT_MAX_FAILURES = 5
LOCKOUT_WINDOW_SECONDS = 300


def _lockout_key(*, request: HttpRequest, username: str) -> str:
    username_lower = username.strip().lower()
    remote_addr = request.META.get("REMOTE_ADDR", "")
    return f"accounts:login_failures:{username_lower}:{remote_addr}"


def is_login_locked(*, request: HttpRequest, username: str) -> bool:
    """Return True if the username/IP pair has exceeded the failure limit."""
    failures = cache.get(_lockout_key(request=request, username=username), 0)
    return failures >= LOCKOUT_MAX_FAILURES


def record_login_failure(*, request: HttpRequest, username: str) -> None:
    """Increment the failure counter for the username/IP pair.

    Uses ``cache.incr``: the read-modify-write it replaces could lose
    increments under concurrent attempts, weakening the lockout. The window
    starts at the first recorded failure.
    """
    key = _lockout_key(request=request, username=username)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=LOCKOUT_WINDOW_SECONDS)


def clear_login_failures(*, request: HttpRequest, username: str) -> None:
    """Reset the failure counter for the username/IP pair."""
    cache.delete(_lockout_key(request=request, username=username))
