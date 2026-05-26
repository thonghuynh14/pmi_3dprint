"""Test settings - pytest. Tối ưu cho tốc độ + isolation."""

from .base import *  # noqa: F401, F403

DEBUG = False
TESTING = True

# In-memory password hasher = test nhanh hơn ~10x
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Storage: local FS để test không cần MinIO
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Celery: eager mode (chạy sync, không cần worker)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email: locmem để assert outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Field encryption: dùng fixed key cho test (không secure, chỉ test)
FIELD_ENCRYPTION_KEY = "kRtT1AINv8Aj9D2A9SgYUFKQTbF_dwYO8oWp9F0Y8N0="

# Logging: tắt tiếng cho output test sạch
LOGGING["root"]["level"] = "ERROR"  # noqa: F405
