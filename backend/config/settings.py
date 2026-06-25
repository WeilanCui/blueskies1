from pathlib import Path

import environ
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")  # pyright: ignore[reportArgumentType]
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])  # pyright: ignore[reportArgumentType]

if not DEBUG and SECRET_KEY in {"change-me", "change-me-in-development"}:
    raise ImproperlyConfigured("Set a strong DJANGO_SECRET_KEY before running production.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "core",
    "literature",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="blueskies"),  # pyright: ignore[reportArgumentType]
        "USER": env("POSTGRES_USER", default="blueskies"),  # pyright: ignore[reportArgumentType]
        "PASSWORD": env("POSTGRES_PASSWORD", default="blueskies"),  # pyright: ignore[reportArgumentType]
        "HOST": env("POSTGRES_HOST", default="db"),  # pyright: ignore[reportArgumentType]
        "PORT": env("POSTGRES_PORT", default="5432"),  # pyright: ignore[reportArgumentType]
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],  # pyright: ignore[reportArgumentType]
)
CORS_ALLOW_CREDENTIALS = env.bool("DJANGO_CORS_ALLOW_CREDENTIALS", default=False)  # pyright: ignore[reportArgumentType]
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])  # pyright: ignore[reportArgumentType]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")  # pyright: ignore[reportArgumentType]
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG)  # pyright: ignore[reportArgumentType]
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = env("DJANGO_CSRF_COOKIE_SAMESITE", default="Lax")  # pyright: ignore[reportArgumentType]
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG)  # pyright: ignore[reportArgumentType]

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)  # pyright: ignore[reportArgumentType]
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)  # pyright: ignore[reportArgumentType]
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,  # pyright: ignore[reportArgumentType]
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)  # pyright: ignore[reportArgumentType]
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DJANGO_THROTTLE_ANON", default="120/min"),  # pyright: ignore[reportArgumentType]
        "user": env("DJANGO_THROTTLE_USER", default="600/min"),  # pyright: ignore[reportArgumentType]
        "auth": env("DJANGO_THROTTLE_AUTH", default="10/min"),  # pyright: ignore[reportArgumentType]
        "signup": env("DJANGO_THROTTLE_SIGNUP", default="5/hour"),  # pyright: ignore[reportArgumentType]
        "contact": env("DJANGO_THROTTLE_CONTACT", default="20/min"),  # pyright: ignore[reportArgumentType]
        "formulation_submit": env("DJANGO_THROTTLE_FORMULATION_SUBMIT", default="20/hour"),  # pyright: ignore[reportArgumentType]
    },
}

INCI_API_KEY = env("INCI_API_KEY", default="")  # pyright: ignore[reportArgumentType]
INCI_API_BASE = env("INCI_API_BASE", default="https://inciapi.com/v1")  # pyright: ignore[reportArgumentType]

SKINCARE_API_BASE = env(
    "SKINCARE_API_BASE",
    default="https://skincare-api.herokuapp.com",  # pyright: ignore[reportArgumentType]
)

EPA_UV_API_BASE = env(
    "EPA_UV_API_BASE",
    default="https://data.epa.gov/efservice",  # pyright: ignore[reportArgumentType]
)
EPA_UV_CACHE_MINUTES = env.int("EPA_UV_CACHE_MINUTES", default=180)  # pyright: ignore[reportArgumentType]
EPA_UV_REQUEST_TIMEOUT_SECONDS = env.int("EPA_UV_REQUEST_TIMEOUT_SECONDS", default=8)  # pyright: ignore[reportArgumentType]

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")  # pyright: ignore[reportArgumentType]
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")  # pyright: ignore[reportArgumentType]
LITERATURE_EXTRACTOR = env("LITERATURE_EXTRACTOR", default="auto")  # pyright: ignore[reportArgumentType]

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")  # pyright: ignore[reportArgumentType]
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")  # pyright: ignore[reportArgumentType]
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = {
    "daily-literature-discovery": {
        "task": "core.tasks.daily_literature_discovery_task",
        "schedule": crontab(
            minute=env.int("LITERATURE_DAILY_MINUTE", default=15),  # pyright: ignore[reportArgumentType]
            hour=env.int("LITERATURE_DAILY_HOUR", default=3),  # pyright: ignore[reportArgumentType]
        ),
        "kwargs": {
            "compound_limit": env.int("LITERATURE_DAILY_COMPOUND_LIMIT", default=25),  # pyright: ignore[reportArgumentType]
            "backfill_limit": env.int("LITERATURE_DAILY_BACKFILL_LIMIT", default=-1),  # pyright: ignore[reportArgumentType]
            "event_limit": env.int("LITERATURE_DAILY_EVENT_LIMIT", default=100),  # pyright: ignore[reportArgumentType]
            "max_articles": env.int("LITERATURE_DAILY_MAX_ARTICLES", default=5),  # pyright: ignore[reportArgumentType]
            "max_related": env.int("LITERATURE_DAILY_MAX_RELATED", default=3),  # pyright: ignore[reportArgumentType]
            "enrich": env.bool("LITERATURE_DAILY_ENRICH", default=False),  # pyright: ignore[reportArgumentType]
        },
    },
}
