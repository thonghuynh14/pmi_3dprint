"""Dev settings - local Docker (postgres + redis + minio)."""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Storage: dùng MinIO local (giả lập S3)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": "media-assets",
            "endpoint_url": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "region_name": "us-east-1",
            "use_ssl": False,
            "addressing_style": "path",
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Lỏng CORS cho dev
CORS_ALLOW_ALL_ORIGINS = True
