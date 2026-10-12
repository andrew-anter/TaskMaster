FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the Tailwind standalone CLI (pinned to the version used by the project)
ARG TARGETARCH
RUN case "${TARGETARCH:-amd64}" in \
        amd64) tailwind_arch=x64 ;; \
        arm64) tailwind_arch=arm64 ;; \
        *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.10/tailwindcss-linux-${tailwind_arch}" -o /usr/local/bin/tailwindcss \
    && chmod +x /usr/local/bin/tailwindcss

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Build the Tailwind CSS used by the templates
RUN ./build-css.sh build

# Collect static files (a build-only SECRET_KEY is required by the settings)
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

# Run as a non-root user that owns the application directory
RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app
USER app

# Expose the port
EXPOSE 8000

# Apply migrations/cache table on startup and hand off to the given command
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "core.wsgi:application"]
