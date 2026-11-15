from django.conf import settings
from django.core.cache import caches
from django.http import HttpRequest

LOCKOUT_MAX_FAILURES = 5
LOCKOUT_WINDOW_SECONDS = 300

cache = caches["lockout"]


def _client_ip(request: HttpRequest) -> str:
    """Return the client IP for the lockout key.

    X-Forwarded-For is client-supplied, so it is only read when a proxy is
    declared to overwrite it; the first hop is then the original client.
    """
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.META.get("REMOTE_ADDR", "")


def _lockout_key(*, request: HttpRequest, username: str) -> str:
    username_lower = username.strip().lower()
    return f"accounts:login_failures:{username_lower}:{_client_ip(request)}"


def is_login_locked(*, request: HttpRequest, username: str) -> bool:
    """Return True if the username/IP pair has exceeded the failure limit."""
    failures = cache.get(_lockout_key(request=request, username=username), 0)
    return failures >= LOCKOUT_MAX_FAILURES


def record_login_failure(*, request: HttpRequest, username: str) -> None:
    """Count one failed attempt for the username/IP pair.

    ``add`` starts the window once (fixed from the first failure, not sliding)
    and ``incr`` is atomic on Redis and LocMemCache. On the DatabaseCache
    fallback ``incr`` is a read-modify-write that also refreshes the TTL, so
    increments and the window are only approximate.
    """
    key = _lockout_key(request=request, username=username)
    if cache.add(key, 1, timeout=LOCKOUT_WINDOW_SECONDS):
        return
    try:
        cache.incr(key)
    except ValueError:
        # Expired between add() and incr(): start a fresh window.
        cache.set(key, 1, timeout=LOCKOUT_WINDOW_SECONDS)


def clear_login_failures(*, request: HttpRequest, username: str) -> None:
    """Reset the failure counter for the username/IP pair."""
    cache.delete(_lockout_key(request=request, username=username))
