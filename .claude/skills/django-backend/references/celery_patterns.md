# Celery Patterns

## Queue setup

```python
# config/celery.py
import os
from celery import Celery
from kombu import Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Separate queues by priority + channel
app.conf.task_queues = (
    Queue('default'),
    Queue('shopee_sync'),
    Queue('lazada_sync'),
    Queue('tiki_sync'),
    Queue('webhooks'),
    Queue('reconcile'),
    Queue('file_processing'),  # STL → GLB
)

app.conf.task_routes = {
    'apps.channels.tasks.push_to_shopee*': {'queue': 'shopee_sync'},
    'apps.channels.tasks.push_to_lazada*': {'queue': 'lazada_sync'},
    'apps.channels.tasks.push_to_tiki*': {'queue': 'tiki_sync'},
    'apps.channels.tasks.process_*_webhook': {'queue': 'webhooks'},
    'apps.channels.tasks.reconcile_*': {'queue': 'reconcile'},
    'apps.design_files.tasks.*': {'queue': 'file_processing'},
}
```

## Idempotent task pattern

```python
# apps/channels/tasks.py
from celery import shared_task
from django.db import transaction
from apps.channels.models import ProcessedEvent

@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=2,           # 2, 4, 8, 16...
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def process_shopee_order_webhook(self, payload: dict):
    """Idempotent qua event_id."""
    event_id = payload.get('event_id')
    if not event_id:
        return {'status': 'ignored', 'reason': 'no event_id'}
    
    # Atomic insert event_id → skip if exists
    with transaction.atomic():
        _, created = ProcessedEvent.objects.get_or_create(
            external_event_id=event_id,
            source='shopee',
            defaults={'payload': payload},
        )
        if not created:
            return {'status': 'skipped', 'reason': 'duplicate'}
        
        # ... actual processing
    
    return {'status': 'processed', 'event_id': event_id}
```

## Stock sync fan-out

```python
# apps/skus/tasks.py
from celery import shared_task, group

@shared_task
def stock_sync_fanout(variant_id: str, new_stock: int):
    """Khi master stock change → fan-out cập nhật mọi channel."""
    from apps.channels.models import ChannelListing
    
    listings = ChannelListing.objects.filter(
        variant_id=variant_id,
        status='synced',
    ).values('id', 'channel')
    
    tasks = []
    for listing in listings:
        if listing['channel'] == 'shopee':
            tasks.append(push_stock_to_shopee.s(listing['id'], new_stock))
        elif listing['channel'] == 'lazada':
            tasks.append(push_stock_to_lazada.s(listing['id'], new_stock))
        elif listing['channel'] == 'tiki':
            tasks.append(push_stock_to_tiki.s(listing['id'], new_stock))
    
    group(tasks).apply_async()
```

## Periodic reconcile (Celery beat)

```python
# config/settings/base.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'reconcile-shopee-every-6h': {
        'task': 'apps.channels.tasks.reconcile_shopee',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'reconcile-lazada-every-6h': {
        'task': 'apps.channels.tasks.reconcile_lazada',
        'schedule': crontab(minute=15, hour='*/6'),
    },
    'reconcile-tiki-every-6h': {
        'task': 'apps.channels.tasks.reconcile_tiki',
        'schedule': crontab(minute=30, hour='*/6'),
    },
    'cleanup-old-audit-logs-daily': {
        'task': 'apps.core.tasks.cleanup_old_audit_logs',
        'schedule': crontab(minute=0, hour=3),
    },
}
```

## Dead letter handling

```python
@shared_task(bind=True, max_retries=5)
def critical_task(self, payload):
    try:
        # ...
        pass
    except RetryableError as e:
        raise self.retry(exc=e)
    except Exception as e:
        # After max_retries exhausted, dump to dead letter table
        from apps.core.models import DeadLetter
        DeadLetter.objects.create(
            task_name=self.name,
            payload=payload,
            error=str(e),
            traceback=traceback.format_exc(),
            attempt_count=self.request.retries,
        )
        # Alert ops
        alert_ops.delay(task=self.name, error=str(e))
```

## Best practices checklist

- [ ] **Idempotent**: dùng `external_event_id` hoặc business unique key
- [ ] **Atomic**: wrap DB writes trong `@transaction.atomic`
- [ ] **Retry config**: backoff + jitter, max_retries hợp lý
- [ ] **Timeout**: set `soft_time_limit` cho task gọi external API
- [ ] **Logging**: structured log với task_id, args
- [ ] **Monitor**: Flower hoặc Celery Insights
- [ ] **Dead letter**: persist payload khi exhausted retries
- [ ] **Test**: dùng `CELERY_TASK_ALWAYS_EAGER=True` trong test settings
