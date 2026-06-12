"""
Base settings - chung cho mọi environment.

Override trong dev.py / prod.py / test.py.
Đọc env qua django-environ. KHÔNG hard-code secret ở đây.
"""

from datetime import timedelta
from pathlib import Path

import environ

# =============================================================================
# Paths
# =============================================================================
# BASE_DIR = .../backend/  (parent của config/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# Env loading
# =============================================================================
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, []),
    DATABASE_CONN_MAX_AGE=(int, 60),
    DATABASE_DISABLE_SERVER_SIDE_CURSORS=(bool, False),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 15),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    STORAGE_USE_SSL=(bool, False),
)

# Load .env nếu tồn tại (dev). Prod inject env qua hệ thống host (Railway / Render / ...).
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# =============================================================================
# Core
# =============================================================================
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-override-in-env")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# =============================================================================
# Apps
# =============================================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "django_extensions",
    "guardian",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.skus",
]

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# Middleware
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =============================================================================
# Database
# =============================================================================
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgresql://pim_user:pim_pass@localhost:5432/pim_dev",
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env("DATABASE_CONN_MAX_AGE")
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env(
    "DATABASE_DISABLE_SERVER_SIDE_CURSORS"
)
# psycopg3 driver
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# Auth
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

# =============================================================================
# I18N / Time
# =============================================================================
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static / Media
# =============================================================================
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# =============================================================================
# DRF
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Cookie-based: đọc access_token từ httpOnly cookie. Mặc định cho FE web.
        "apps.accounts.authentication.CookieJWTAuthentication",
        # Header Bearer: fallback cho cURL test + Postman + bot/CI.
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# =============================================================================
# JWT
# =============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOWED_ORIGINS = env("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# drf-spectacular
# =============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "3D Printing PIM API",
    "DESCRIPTION": "API quản lý sản phẩm & SKU in 3D đa kênh.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# =============================================================================
# Celery
# =============================================================================
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 min hard limit
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"
# Queues mỗi marketplace tách riêng (xem ARCHITECTURE.md)
CELERY_TASK_ROUTES = {
    "apps.channels.tasks.shopee.*": {"queue": "shopee_sync"},
    "apps.channels.tasks.lazada.*": {"queue": "lazada_sync"},
    "apps.channels.tasks.tiki.*": {"queue": "tiki_sync"},
    "apps.channels.tasks.webhooks.*": {"queue": "webhooks"},
    "apps.channels.tasks.reconcile.*": {"queue": "reconcile"},
    "apps.design_files.tasks.*": {"queue": "file_processing"},
}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# =============================================================================
# Storage (S3-compatible: MinIO dev, Supabase Storage prod)
# =============================================================================
STORAGE_BUCKET_DESIGN_FILES = env(
    "STORAGE_BUCKET_DESIGN_FILES", default="design-files"
)
STORAGE_BUCKET_MEDIA = env("STORAGE_BUCKET_MEDIA", default="media-assets")
STORAGE_ENDPOINT_URL = env("STORAGE_ENDPOINT_URL", default="http://localhost:9000")
STORAGE_ACCESS_KEY = env("STORAGE_ACCESS_KEY", default="")
STORAGE_SECRET_KEY = env("STORAGE_SECRET_KEY", default="")
STORAGE_REGION = env("STORAGE_REGION", default="us-east-1")
STORAGE_USE_SSL = env("STORAGE_USE_SSL")
STORAGE_CDN_URL = env("STORAGE_CDN_URL", default=STORAGE_ENDPOINT_URL)

# =============================================================================
# Field encryption (cho MarketplaceCredential tokens)
# =============================================================================
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# =============================================================================
# Marketplace credentials (app-level)
# =============================================================================
SHOPEE_PARTNER_ID = env("SHOPEE_PARTNER_ID", default="")
SHOPEE_PARTNER_KEY = env("SHOPEE_PARTNER_KEY", default="")
SHOPEE_SANDBOX = env.bool("SHOPEE_SANDBOX", default=True)

LAZADA_APP_KEY = env("LAZADA_APP_KEY", default="")
LAZADA_APP_SECRET = env("LAZADA_APP_SECRET", default="")
LAZADA_REGION = env("LAZADA_REGION", default="VN")

TIKI_CLIENT_ID = env("TIKI_CLIENT_ID", default="")
TIKI_CLIENT_SECRET = env("TIKI_CLIENT_SECRET", default="")

# =============================================================================
# Cost defaults VN (BR-005)
# =============================================================================
ELECTRICITY_PRICE_VND_PER_KWH = env.int(
    "ELECTRICITY_PRICE_VND_PER_KWH", default=3000
)
DEFAULT_FAILURE_BUFFER_PERCENT = env.int(
    "DEFAULT_FAILURE_BUFFER_PERCENT", default=10
)
DEFAULT_MARKUP_MULTIPLIER = env.float(
    "DEFAULT_MARKUP_MULTIPLIER", default=2.5
)
DEFAULT_LABOR_RATE_VND_PER_HOUR = env.int(
    "DEFAULT_LABOR_RATE_VND_PER_HOUR", default=50000
)

# =============================================================================
# Email
# =============================================================================
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="noreply@3dprintpim.local"
)

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
