# Migration Patterns (Zero-Downtime)

## Nguyên tắc

Production migration phải **backward-compatible** — code cũ chạy được với schema mới và ngược lại trong khoảng thời gian deploy. Pattern: **expand → migrate → contract**.

## Safe operations (chạy được không downtime)

✅ Add nullable column  
✅ Add column với default (Postgres 11+ là instant cho default constant)  
✅ Add table mới  
✅ Add index CONCURRENTLY  
✅ Drop unused index  
✅ Rename column qua deprecate + dual-write  

## Unsafe operations (cẩn thận)

⚠️ Add NOT NULL column on existing table → cần 2 step: add nullable, backfill, alter NOT NULL  
⚠️ Drop column → cần deprecate code trước  
⚠️ Rename column → expand + contract  
⚠️ Change column type → tạo column mới + dual-write + cutover  
⚠️ Add unique constraint trên existing → check data trước  
⚠️ Add FK trên large table → cần CONCURRENTLY  

## Pattern: Add NOT NULL column với default

```python
# Step 1: migration 0010 — add nullable column
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='variant',
            name='is_made_to_order',
            field=models.BooleanField(null=True),
        ),
    ]

# Deploy + run script backfill data
# UPDATE skus_variants SET is_made_to_order = false WHERE is_made_to_order IS NULL;

# Step 2: migration 0011 — alter to NOT NULL
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "UPDATE skus_variants SET is_made_to_order = false WHERE is_made_to_order IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='variant',
            name='is_made_to_order',
            field=models.BooleanField(default=False),
        ),
    ]
```

## Pattern: Rename column

```python
# Step 1: Add new column, dual-write trong code
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='variant',
            name='layer_resolution_mm',
            field=models.DecimalField(max_digits=4, decimal_places=3, null=True),
        ),
        migrations.RunPython(copy_old_to_new, copy_new_to_old),
    ]

def copy_old_to_new(apps, schema_editor):
    Variant = apps.get_model('skus', 'Variant')
    Variant.objects.update(layer_resolution_mm=F('layer_thickness'))

def copy_new_to_old(apps, schema_editor):
    Variant = apps.get_model('skus', 'Variant')
    Variant.objects.update(layer_thickness=F('layer_resolution_mm'))

# Step 2: Deploy code dùng layer_resolution_mm
# Step 3: Drop old column
```

## Pattern: Add index CONCURRENTLY

Django mặc định `CREATE INDEX` block bảng. Production cần CONCURRENTLY:

```python
# apps/skus/migrations/0012_variant_attributes_gin.py
from django.contrib.postgres.operations import AddIndexConcurrently
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY
    
    operations = [
        AddIndexConcurrently(
            model_name='variant',
            index=GinIndex(fields=['attributes'], name='idx_variant_attrs_gin'),
        ),
    ]
```

## Pattern: Data migration (large table)

```python
# Đối với table > 1M rows, không UPDATE 1 phát toàn bộ
from django.db import migrations

def backfill_in_batches(apps, schema_editor):
    Variant = apps.get_model('skus', 'Variant')
    batch_size = 1000
    last_id = ''
    
    while True:
        batch = list(Variant.objects.filter(
            id__gt=last_id, license_allows_commercial__isnull=True
        ).order_by('id').only('id', 'design_file').select_related('design_file')[:batch_size])
        
        if not batch:
            break
        
        for v in batch:
            v.license_allows_commercial = (
                v.design_file.license_type not in ['cc_by_nc', 'cc_by_nc_sa', 'cc_by_nc_nd']
                if v.design_file else None
            )
        
        Variant.objects.bulk_update(batch, ['license_allows_commercial'], batch_size=500)
        last_id = batch[-1].id


class Migration(migrations.Migration):
    operations = [migrations.RunPython(backfill_in_batches, migrations.RunPython.noop)]
```

## Pattern: Drop column safely

```python
# Step 1 (release N): Code không đọc/ghi column nữa, vẫn còn trong DB
# Step 2 (release N+1): Drop column
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveField(model_name='variant', name='old_field'),
    ]
```

## Pattern: Add UNIQUE constraint

```python
# Step 1: Check duplicate data trước
# python manage.py shell:
# Variant.objects.values('sku').annotate(c=Count('id')).filter(c__gt=1)

# Step 2: Fix duplicates (rename hoặc merge)

# Step 3: Add constraint
class Migration(migrations.Migration):
    operations = [
        migrations.AddConstraint(
            model_name='variant',
            constraint=models.UniqueConstraint(fields=['sku'], name='uq_variant_sku'),
        ),
    ]
```

## Reversibility

Mọi migration phải có `reverse_code` hoặc `reverse_sql`. Không dùng `reverse_code=migrations.RunPython.noop` cho data migration nếu rollback có thể cần lại data cũ.

```python
def forward(apps, schema_editor):
    # ...

def reverse(apps, schema_editor):
    # ...

class Migration(migrations.Migration):
    operations = [migrations.RunPython(forward, reverse)]
```

## Testing migration

```python
# tests/test_migration_0015.py
import pytest
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestMigration0015(MigratorTestCase):
    migrate_from = ('skus', '0014_previous')
    migrate_to = ('skus', '0015_add_license_flags')
    
    def prepare(self):
        Variant = self.old_state.apps.get_model('skus', 'Variant')
        DesignFile = self.old_state.apps.get_model('design_files', 'DesignFile')
        
        nc_file = DesignFile.objects.create(license_type='cc_by_nc')
        Variant.objects.create(design_file=nc_file, sku='TEST-01')
    
    def test_license_flag_backfilled(self):
        Variant = self.new_state.apps.get_model('skus', 'Variant')
        v = Variant.objects.get(sku='TEST-01')
        assert v.license_allows_commercial is False
```

## Checklist trước khi run migration trên production

- [ ] Tested trên staging với production-like data volume
- [ ] Có rollback plan (reverse migration tested)
- [ ] Backup DB ngay trước migration
- [ ] Estimate time: `EXPLAIN ANALYZE` các large operations
- [ ] Run trong maintenance window nếu unavoidable
- [ ] Monitor: alerts cho lock wait, replication lag
- [ ] CONCURRENTLY cho index trên large table
- [ ] Batch update cho > 100K rows
- [ ] Drop column trong release riêng (không cùng release với code change)

## Lock-aware migration

```python
# Set statement_timeout + lock_timeout
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL("SET lock_timeout = '5s';", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("SET statement_timeout = '30s';", reverse_sql=migrations.RunSQL.noop),
        # ... actual operation
    ]
```
