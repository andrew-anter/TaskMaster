#!/bin/sh
set -e

# Schema setup is opt-in so worker/beat containers can run the same image
# without racing the web container's migrations (set RUN_MIGRATIONS=0 there).
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
fi

exec "$@"
