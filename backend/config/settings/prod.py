"""Prod settings - Supabase Postgres + Supabase Storage."""

from .base import *  # noqa: F401, F403

DEBUG = False

# Security headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 năm
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Storage: Supabase Storage (qua S3 endpoint)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": STORAGE_BUCKET_MEDIA,  # noqa: F405
            "endpoint_url": STORAGE_ENDPOINT_URL,  # noqa: F405
            "access_key": STORAGE_ACCESS_KEY,  # noqa: F405
            "secret_key": STORAGE_SECRET_KEY,  # noqa: F405
            "region_name": STORAGE_REGION,  # noqa: F405
            "use_ssl": STORAGE_USE_SSL,  # noqa: F405
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
