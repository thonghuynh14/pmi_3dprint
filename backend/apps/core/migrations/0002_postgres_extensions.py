"""Enable Postgres extensions needed by domain migrations.

postgres-init.sql của docker compose chỉ chạy lúc container khởi tạo
container — nó tạo extensions trên `pim_dev`. Test DB (`test_pim_dev`)
pytest-django tạo fresh sẽ KHÔNG có init script → cần migration này để
mọi DB (dev, test, staging, prod, Supabase) đều có cùng extensions
trước khi domain migrations chạy.

CREATE EXTENSION IF NOT EXISTS là idempotent → re-run trên DB đã có
extensions vô hại.
"""

from django.contrib.postgres.operations import (
    BtreeGinExtension,
    CryptoExtension,
    TrigramExtension,
    UnaccentExtension,
)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        CryptoExtension(),
        TrigramExtension(),
        UnaccentExtension(),
        BtreeGinExtension(),
        # uuid-ossp + ltree không có wrapper trong django.contrib.postgres.operations
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
            reverse_sql='DROP EXTENSION IF EXISTS "uuid-ossp";',
        ),
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS "ltree";',
            reverse_sql='DROP EXTENSION IF EXISTS "ltree";',
        ),
    ]
