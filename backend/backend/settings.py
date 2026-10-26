"""
Настройки Django для продакшена.

Все секреты и окружение-зависимые значения берутся из переменных окружения
(см. .env.example в корне проекта). Значения по умолчанию — безопасные:
DEBUG выключен, хосты и SECRET_KEY обязательны.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Базовая безопасность
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)
# `manage.py test` работает без настройки окружения (секреты и БД тестовые).
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
DEV = DEBUG or TESTING

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if DEV:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production-" + "x" * 30
    else:
        raise ImproperlyConfigured("Переменная окружения SECRET_KEY обязательна (DEBUG выключен).")
if not DEV and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("dev-only") or SECRET_KEY.startswith("django-insecure")):
    raise ImproperlyConfigured("SECRET_KEY слишком короткий или небезопасный: нужно 50+ случайных символов.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver" if DEV else "")
if not DEV and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("ALLOWED_HOSTS должен содержать конкретные домены (без '*').")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Секретный путь админки (не /admin/). Задаётся в окружении, без слэшей по краям.
ADMIN_URL = os.getenv("ADMIN_URL", "admin" if DEV else "").strip("/")
if not ADMIN_URL:
    raise ImproperlyConfigured("ADMIN_URL обязателен: задайте непредсказуемый путь админки, например 'panel-x7k2q9'.")

# ---------------------------------------------------------------------------
# Приложения и middleware
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "phonenumber_field",
    "axes",
    "blaknot_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"

# ---------------------------------------------------------------------------
# База данных и кэш
# ---------------------------------------------------------------------------
# Прод: DATABASE_URL=postgres://user:pass@host:5432/dbname
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
        conn_health_checks=True,
    )
}
if not DEV and DATABASES["default"]["ENGINE"].endswith("sqlite3") and not env_bool("ALLOW_SQLITE"):
    raise ImproperlyConfigured("В продакшене используйте PostgreSQL (DATABASE_URL).")

# Кэш в БД: общий для всех воркеров gunicorn (нужен троттлингу и защите от перебора).
# Таблица создаётся командой `manage.py createcachetable`.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# ---------------------------------------------------------------------------
# Пользователи и пароли
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "blaknot_app.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Защита от подбора паролей (django-axes): блокировка пары логин+IP после 5 неудач.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_CLIENT_IP_CALLABLE = "blaknot_app.utils.client_ip"
AXES_ENABLED = env_bool("AXES_ENABLED", True)

# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Статика и медиа (в проде отдаёт nginx; админка — через whitenoise)
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

# Лимиты загрузок (защита от DoS большими телами запросов)
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200
PROFILE_IMAGE_MAX_BYTES = 2 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF + JWT
# ---------------------------------------------------------------------------
_renderers = ["rest_framework.renderers.JSONRenderer"]
if DEBUG:
    _renderers.append("rest_framework.renderers.BrowsableAPIRenderer")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": _renderers,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "blaknot_app.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "login": "10/min",
        "register": "5/hour",
        "refresh": "60/min",
        "password": "5/hour",
    },
    # Бэкенд закрыт от интернета и вызывается только фронтом (1 прокси-хоп):
    # реальный IP пользователя фронт передаёт в X-Forwarded-For.
    "NUM_PROXIES": 1,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# HTTPS и заголовки безопасности
# ---------------------------------------------------------------------------
USE_HTTPS = env_bool("USE_HTTPS", not DEV)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT =False
    # Внутренние вызовы API от фронта идут по http внутри docker-сети — их не редиректим.
    SECURE_REDIRECT_EXEMPT = [r"^api/", r"^healthz/"]
    SECURE_HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# Почта
# ---------------------------------------------------------------------------
if os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@localhost")

# ---------------------------------------------------------------------------
# Логи (stdout — их собирает docker / journald)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "axes": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# Sentry (необязательно): задайте SENTRY_DSN и добавьте sentry-sdk в requirements.
if os.getenv("SENTRY_DSN"):
    import sentry_sdk

    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], send_default_pii=False, traces_sample_rate=0.0)
