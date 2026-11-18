import os
import secrets
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(os.path.join(BASE_DIR, "core", ".env"))


SECRET_KEY = env("SECRET_KEY", default="")  # type: ignore[reportArgumentType]
DEBUG = env.bool("DEBUG", default=False)  # type: ignore[reportArgumentType]

if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set when DEBUG is False. Generate one with: "
            'python -c "from django.core.management.utils import '
            'get_random_secret_key; print(get_random_secret_key())"'
        )
    # Ephemeral per-process key: dev needs no configuration, and unlike a
    # checked-in placeholder it can never leak into a production deployment.
    SECRET_KEY = secrets.token_urlsafe(50)

if DEBUG:
    try:
        import django_stubs_ext
    except ImportError:
        # Dev-only dependency, absent from the --no-dev container image.
        pass
    else:
        django_stubs_ext.monkeypatch()


ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Admin configuration for error notifications
ADMINS = [("Admin", env("ADMIN_EMAIL", default="admin@example.com"))]  # type: ignore[reportArgumentType]
SERVER_EMAIL = env("SERVER_EMAIL", default="root@example.com")  # type: ignore[reportArgumentType]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "django_htmx",
    "rest_framework",
    "corsheaders",
    "colorfield",
    # django allauth
    "allauth",
    "allauth.account",
    # Social Accounts
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Main apps
    "tasks",
    "accounts",
    "labels",
    "notifications",
    "common",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "common.middleware.HtmxVaryMiddleware",
]

# Security Settings for Production
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # type: ignore[reportArgumentType]
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)  # type: ignore[reportArgumentType]
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)  # type: ignore[reportArgumentType]
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # type: ignore[reportArgumentType]
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        default=True,  # type: ignore[reportArgumentType]
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)  # type: ignore[reportArgumentType]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"

# Only enable when a reverse proxy overwrites X-Forwarded-For; otherwise the
# header is client-supplied and would let clients choose their lockout bucket.
TRUST_X_FORWARDED_FOR = env.bool("TRUST_X_FORWARDED_FOR", default=False)  # type: ignore[reportArgumentType]

ROOT_URLCONF = "core.urls"
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_notifications_count",
            ],
        },
    },
]
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")  # type: ignore

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": env("GOOGLE_SECRET", default=""),  # pyright: ignore
        }
    },
}


WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")  # type: ignore[reportArgumentType]
}

# Database connection optimization for production
if not DEBUG:
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)  # type: ignore[reportArgumentType]
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    # Only add connect_timeout for PostgreSQL (not supported by SQLite)
    if DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
        DATABASES["default"]["OPTIONS"] = {
            "connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=10),  # type: ignore[reportArgumentType]
        }

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    },
    "notifications": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "notifications-count",
    },
}

if not DEBUG:
    CACHE_MAX_ENTRIES = env.int("CACHE_MAX_ENTRIES", default=10000)  # type: ignore[reportArgumentType]
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "cache_table",
            "TIMEOUT": env.int("CACHE_TIMEOUT", default=300),  # type: ignore[reportArgumentType]
            "OPTIONS": {
                "MAX_ENTRIES": CACHE_MAX_ENTRIES,
            },
        },
        "notifications": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            # Own table: culling notification keys must not evict other keys.
            "LOCATION": "notifications_cache_table",
            "TIMEOUT": env.int("CACHE_TIMEOUT", default=300),  # type: ignore[reportArgumentType]
            "OPTIONS": {
                "MAX_ENTRIES": CACHE_MAX_ENTRIES,
            },
        },
    }

# Login lockout counters need atomic increments: Redis INCR when a cache server
# is configured, otherwise a copy of the default backend (LocMemCache in dev).
REDIS_CACHE_URL = env("REDIS_CACHE_URL", default="")  # type: ignore[reportArgumentType]
if REDIS_CACHE_URL:
    CACHES["lockout"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
    }
else:
    CACHES["lockout"] = {**CACHES["default"]}

# Session configuration
# cached_db keeps sessions readable when the cache entry is evicted.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=1209600)  # type: ignore[reportArgumentType]  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool(
    "SESSION_EXPIRE_AT_BROWSER_CLOSE",
    default=False,  # type: ignore[reportArgumentType]
)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("API_THROTTLE_ANON", default="100/hour"),  # type: ignore[reportArgumentType]
        "user": env("API_THROTTLE_USER", default="1000/hour"),  # type: ignore[reportArgumentType]
    },
}


# Celery / Valkey (Redis-compatible) configuration
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="redis://127.0.0.1:6379/0",  # type: ignore[reportArgumentType]
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://127.0.0.1:6379/0",  # type: ignore[reportArgumentType]
)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)  # type: ignore[reportArgumentType]
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Notification retention (enforced by the daily cleanup beat task)
NOTIFICATIONS_READ_RETENTION_DAYS = env.int(
    "NOTIFICATIONS_READ_RETENTION_DAYS",
    default=30,  # type: ignore[reportArgumentType]
)
NOTIFICATIONS_UNREAD_RETENTION_DAYS = env.int(
    "NOTIFICATIONS_UNREAD_RETENTION_DAYS",
    default=90,  # type: ignore[reportArgumentType]
)

CELERY_BEAT_SCHEDULE = {
    "generate-task-reminder-notifications": {
        "task": "tasks.tasks.generate_reminder_notifications",
        "schedule": env.int(
            "CELERY_BEAT_REMINDERS_INTERVAL_SECONDS",
            default=900,  # type: ignore[reportArgumentType]
        ),
    },
    "cleanup-old-notifications": {
        "task": "notifications.tasks.cleanup_old_notifications",
        "schedule": env.int(
            "CELERY_BEAT_NOTIFICATIONS_CLEANUP_INTERVAL_SECONDS",
            default=86400,  # type: ignore[reportArgumentType]
        ),
    },
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

CELERY_TIMEZONE = TIME_ZONE

STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_URL = "static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))  # type: ignore[reportArgumentType]

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

MEDIA_URL = env("MEDIA_URL", default="/media/")  # type: ignore[reportArgumentType]
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))  # type: ignore[reportArgumentType]

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")  # type: ignore[reportArgumentType]

# Email configuration
_email_backend = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),  # type: ignore[reportArgumentType]
)
_mail_options: dict[str, str | int | bool] = {}
if not DEBUG:
    _mail_options = {
        "host": env("EMAIL_HOST", default="localhost"),  # type: ignore[reportArgumentType]
        "port": env.int("EMAIL_PORT", default=587),  # type: ignore[reportArgumentType]
        "username": env("EMAIL_HOST_USER", default=""),  # type: ignore[reportArgumentType]
        "password": env("EMAIL_HOST_PASSWORD", default=""),  # type: ignore[reportArgumentType]
        "use_tls": env.bool("EMAIL_USE_TLS", default=True),  # type: ignore[reportArgumentType]
        "use_ssl": env.bool("EMAIL_USE_SSL", default=False),  # type: ignore[reportArgumentType]
        "timeout": env.int("EMAIL_TIMEOUT", default=10),  # type: ignore[reportArgumentType]
    }
MAILERS = {
    "default": {
        "BACKEND": _email_backend,
        "OPTIONS": _mail_options,
    },
    "admin-logging": {
        "BACKEND": _email_backend,
        # Preserve AdminEmailHandler's previous fail-silent behavior.
        "OPTIONS": {**_mail_options, "fail_silently": True},
    },
}

# Password hashers - use strong hashers in production
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Account security settings
ACCOUNT_LOGIN_METHODS = {"username", "email"}
# `*` marks a field required; email is validated by allauth's EmailField.
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_FORMS = {
    "reset_password": "accounts.forms.CustomResetPasswordForm",  # nosec B105 (form path, not a secret)
    "reset_password_from_key": "accounts.forms.CustomResetPasswordKeyForm",  # nosec B105 (form path, not a secret)
}
# Replaces allauth's whole default, so keep both components: the per-IP cap
# stops credential stuffing across usernames, the per-key cap stops one account.
ACCOUNT_RATE_LIMITS = {
    "login_failed": env(
        "ACCOUNT_LOGIN_ATTEMPTS_LIMIT",
        default="10/m/ip,5/5m",  # type: ignore[reportArgumentType]
    ),
}

# Logging Configuration
LOG_DIR = BASE_DIR / "logs"
if not DEBUG:
    LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "using": "admin-logging",
            "include_html": not DEBUG,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),  # type: ignore[reportArgumentType]
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

if not DEBUG:
    LOGGING["handlers"]["file"] = {
        "level": "INFO",
        # Rotation delegated to logrotate; safe for multi-process deployments.
        "class": "logging.handlers.WatchedFileHandler",
        "filename": str(LOG_DIR / "django.log"),
        "formatter": "verbose",
    }
    LOGGING["loggers"]["django"]["handlers"].append("file")
    LOGGING["root"]["handlers"].append("file")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SOCIALACCOUNT_LOGIN_ON_GET = True
