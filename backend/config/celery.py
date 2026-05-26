"""Celery application factory.

Worker chạy: celery -A config worker -l info
Beat chạy:   celery -A config beat -l info
Multi-queue: celery -A config worker -Q shopee_sync,lazada_sync -l info
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("3dprint_pim")

# Đọc config từ Django settings, prefix CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks trong INSTALLED_APPS (apps/*/tasks.py)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Smoke test task. Gọi: debug_task.delay()."""
    print(f"Request: {self.request!r}")
