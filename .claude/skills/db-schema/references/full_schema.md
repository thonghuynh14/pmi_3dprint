# Full Schema - 20+ Tables

Định nghĩa đầy đủ Django models cho dự án. Copy-paste được vào `apps/{app}/models/`.

## apps/accounts/models.py

```python
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=32,
        choices=[
            ('super_admin', 'Super Admin'),
            ('catalog_manager', 'Catalog Manager'),
            ('production_manager', 'Production Manager'),
            ('channel_operator', 'Channel Operator'),
            ('designer', 'Designer'),
            ('cashier', 'Cashier'),
        ],
    )
    team = models.CharField(max_length=64, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'accounts_users'
        indexes = [models.Index(fields=['role'])]
```

## apps/catalog/models.py

```python
import uuid
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django_ltree.fields import PathField  # pip install django-ltree
from apps.core.models import TimestampedModel, SoftDeleteModel, AuditedModel


class Brand(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    logo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'catalog_brands'


class Category(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    path = PathField()  # ltree
    code_3 = models.CharField(max_length=3, unique=True)  # FIG, GDT, JWL
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    depth = models.PositiveSmallIntegerField(default=0)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'catalog_categories'
        indexes = [models.Index(fields=['parent']), models.Index(fields=['path'])]


class Product(TimestampedModel, SoftDeleteModel, AuditedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
    
    class LifecycleStage(models.TextChoices):
        IDEA = 'idea'
        CONCEPT = 'concept'
        PROTOTYPE = 'prototype'
        READY = 'ready'
        SELLING = 'selling'
        EOL = 'eol'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    sku_root = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    short_description = models.TextField(blank=True)
    long_description = models.TextField(blank=True)
    
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    primary_category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products_as_primary')
    categories = models.ManyToManyField(Category, through='ProductCategory', related_name='products')
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    lifecycle_stage = models.CharField(max_length=16, choices=LifecycleStage.choices, default=LifecycleStage.IDEA)
    
    default_variant = models.ForeignKey(
        'skus.Variant', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    
    attributes = models.JSONField(default=dict, blank=True)
    tags = ArrayField(models.CharField(max_length=32), default=list, blank=True)
    
    # SEO
    seo_title = models.CharField(max_length=140, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    seo_keywords = ArrayField(models.CharField(max_length=64), default=list, blank=True)
    
    class Meta:
        db_table = 'catalog_products'
        indexes = [
            GinIndex(fields=['attributes']),
            GinIndex(fields=['tags']),
            models.Index(fields=['status', 'lifecycle_stage']),
            models.Index(fields=['sku_root']),
        ]


class ProductCategory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'catalog_product_categories'
        unique_together = [('product', 'category')]


class AttributeDefinition(TimestampedModel):
    """Meta cho dynamic attributes — render form UI từ đây."""
    class Type(models.TextChoices):
        STRING = 'string'
        TEXT = 'text'
        NUMBER = 'number'
        BOOLEAN = 'boolean'
        SELECT = 'select'
        MULTISELECT = 'multiselect'
        DATE = 'date'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120)
    type = models.CharField(max_length=16, choices=Type.choices)
    options = models.JSONField(default=list, blank=True)  # cho SELECT/MULTISELECT
    applies_to = models.CharField(max_length=16, choices=[('product', 'Product'), ('variant', 'Variant')])
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'catalog_attribute_definitions'
```

## apps/skus/models.py

```python
import uuid
from decimal import Decimal
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from apps.core.models import TimestampedModel, SoftDeleteModel, AuditedModel


class Variant(TimestampedModel, SoftDeleteModel, AuditedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft'
        ACTIVE = 'active'
        INACTIVE = 'inactive'
        OOS = 'oos'
        EOL = 'eol'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='variants')
    sku = models.CharField(max_length=32, unique=True)
    barcode = models.CharField(max_length=14, blank=True, db_index=True)
    
    # Variant axes (5 trục đặc thù 3D)
    material = models.ForeignKey('materials.Material', on_delete=models.PROTECT, null=True, blank=True)
    material_color = models.CharField(max_length=32, blank=True)
    size_preset = models.CharField(max_length=16, blank=True)
    layer_resolution_mm = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    infill_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # Physical
    weight_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions_mm = models.JSONField(default=dict, blank=True)
    
    # Dynamic
    attributes = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    is_made_to_order = models.BooleanField(default=False)
    lead_time_hours = models.PositiveSmallIntegerField(default=0)
    
    design_file = models.ForeignKey(
        'design_files.DesignFile',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='variants',
    )
    
    class Meta:
        db_table = 'skus_variants'
        indexes = [
            GinIndex(fields=['attributes']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['barcode']),
            models.Index(fields=['material', 'material_color']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(base_price__gte=0), name='chk_variant_base_price_nonneg'),
            models.CheckConstraint(check=models.Q(cost_price__gte=0), name='chk_variant_cost_price_nonneg'),
            models.CheckConstraint(
                check=models.Q(infill_percent__isnull=True) | (models.Q(infill_percent__gte=0) & models.Q(infill_percent__lte=100)),
                name='chk_variant_infill_range',
            ),
        ]


class SkuCode(models.Model):
    """Abbreviation library cho SKU generation."""
    entity_type = models.CharField(max_length=32)  # color, material, size, category
    value = models.CharField(max_length=64)
    code = models.CharField(max_length=8)
    
    class Meta:
        db_table = 'skus_sku_codes'
        unique_together = [
            ('entity_type', 'value'),
            ('entity_type', 'code'),
        ]
```

## apps/design_files/models.py

```python
import uuid
from django.db import models
from apps.core.models import TimestampedModel, AuditedModel


class DesignFile(TimestampedModel, AuditedModel):
    class Format(models.TextChoices):
        STL = 'stl'
        OBJ = 'obj'
        THREEMF = '3mf'
        STEP = 'step'
        GCODE = 'gcode'
        GLB = 'glb'
        BLEND = 'blend'
    
    class Source(models.TextChoices):
        ORIGINAL = 'original'
        THINGIVERSE = 'thingiverse'
        PRINTABLES = 'printables'
        CULTS3D = 'cults3d'
        MYMINIFACTORY = 'mymf'
        COMMISSION = 'commission'
    
    class License(models.TextChoices):
        CC0 = 'cc0', 'CC0 Public Domain'
        CC_BY = 'cc_by', 'CC BY'
        CC_BY_SA = 'cc_by_sa', 'CC BY-SA'
        CC_BY_ND = 'cc_by_nd', 'CC BY-ND'
        CC_BY_NC = 'cc_by_nc', 'CC BY-NC'
        CC_BY_NC_SA = 'cc_by_nc_sa', 'CC BY-NC-SA'
        CC_BY_NC_ND = 'cc_by_nc_nd', 'CC BY-NC-ND'
        ALL_RIGHTS = 'all_rights_reserved', 'All Rights Reserved'
        CUSTOM = 'custom'
        PROPRIETARY = 'proprietary'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    product = models.ForeignKey('catalog.Product', null=True, blank=True, on_delete=models.SET_NULL, related_name='design_files')
    
    filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=512)  # S3/MinIO key
    cdn_url = models.URLField(blank=True)
    glb_preview_key = models.CharField(max_length=512, blank=True)  # converted GLB
    thumbnail_key = models.CharField(max_length=512, blank=True)
    
    format = models.CharField(max_length=8, choices=Format.choices)
    size_bytes = models.BigIntegerField()
    triangles_count = models.IntegerField(null=True, blank=True)
    bounding_box = models.JSONField(default=dict, blank=True)
    
    # Versioning
    version = models.CharField(max_length=16, default='v1.0')
    parent_file = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_versions')
    changelog = models.TextField(blank=True)
    
    # Source & license
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.ORIGINAL)
    source_url = models.URLField(blank=True)
    source_author = models.CharField(max_length=200, blank=True)
    
    license_type = models.CharField(max_length=32, choices=License.choices)
    license_allows_commercial = models.BooleanField()  # derived
    license_requires_attribution = models.BooleanField()  # derived
    license_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'design_files_files'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['source']),
            models.Index(fields=['license_type']),
            models.Index(fields=['license_allows_commercial']),
        ]
    
    def save(self, *args, **kwargs):
        # Derive license flags
        nc_licenses = ['cc_by_nc', 'cc_by_nc_sa', 'cc_by_nc_nd']
        attribution_licenses = ['cc_by', 'cc_by_sa', 'cc_by_nd', 'cc_by_nc', 'cc_by_nc_sa', 'cc_by_nc_nd']
        self.license_allows_commercial = self.license_type not in nc_licenses
        self.license_requires_attribution = self.license_type in attribution_licenses
        super().save(*args, **kwargs)
```

## apps/materials/models.py

```python
import uuid
from django.db import models
from apps.core.models import TimestampedModel


class Material(TimestampedModel):
    class Type(models.TextChoices):
        FILAMENT = 'filament'
        RESIN = 'resin'
        POWDER = 'powder'
        SUPPORT = 'support'
        PAINT = 'paint'
        GLUE = 'glue'
        PACKAGING = 'packaging'
        OTHER = 'other'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=16, choices=Type.choices)
    subtype = models.CharField(max_length=32, blank=True)  # pla, plaplus, abs, petg, ...
    color = models.CharField(max_length=32, blank=True)
    color_hex = models.CharField(max_length=7, blank=True)
    
    diameter_mm = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # 1.75 / 2.85
    density_g_cm3 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=8, default='g')  # g, ml, kg, piece
    
    supplier = models.ForeignKey('Supplier', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Print settings
    print_temp_min_c = models.IntegerField(null=True, blank=True)
    print_temp_max_c = models.IntegerField(null=True, blank=True)
    bed_temp_min_c = models.IntegerField(null=True, blank=True)
    bed_temp_max_c = models.IntegerField(null=True, blank=True)
    
    # Properties
    requires_enclosure = models.BooleanField(default=False)
    food_safe = models.BooleanField(default=False)
    uv_resistant = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'materials_materials'


class Supplier(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=120)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'materials_suppliers'
```

## apps/manufacturing/models.py

```python
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models
from apps.core.models import TimestampedModel, AuditedModel


class Printer(TimestampedModel):
    class Technology(models.TextChoices):
        FDM = 'fdm'
        SLA = 'sla'
        MSLA = 'msla'
        DLP = 'dlp'
        SLS = 'sls'
        MJF = 'mjf'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
    technology = models.CharField(max_length=8, choices=Technology.choices)
    
    build_volume = models.JSONField(default=dict)  # {x, y, z} mm
    nozzle_sizes = ArrayField(models.DecimalField(max_digits=3, decimal_places=1), default=list, blank=True)
    layer_min_mm = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    layer_max_mm = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    supported_materials = models.ManyToManyField('materials.Material', blank=True, related_name='compatible_printers')
    
    max_temp_nozzle_c = models.IntegerField(null=True, blank=True)
    max_temp_bed_c = models.IntegerField(null=True, blank=True)
    has_enclosure = models.BooleanField(default=False)
    has_ams = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    is_owned = models.BooleanField(default=True)
    location = models.CharField(max_length=64, blank=True)
    
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    lifetime_hours = models.IntegerField(default=5000)
    hours_used = models.IntegerField(default=0)
    wattage = models.IntegerField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'manufacturing_printers'


class BOM(TimestampedModel, AuditedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    variant = models.OneToOneField('skus.Variant', on_delete=models.CASCADE, related_name='bom')
    version = models.CharField(max_length=16, default='v1')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'manufacturing_boms'


class BOMLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name='lines')
    material = models.ForeignKey('materials.Material', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=8, default='g')
    is_primary = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'manufacturing_bom_lines'
        constraints = [models.CheckConstraint(check=models.Q(quantity__gt=0), name='chk_bom_line_qty_positive')]


class VariantCompatiblePrinter(models.Model):
    variant = models.ForeignKey('skus.Variant', on_delete=models.CASCADE, related_name='compatible_printers')
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE, related_name='compatible_variants')
    estimated_minutes = models.IntegerField()
    is_preferred = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'manufacturing_variant_compatible_printers'
        unique_together = [('variant', 'printer')]
```

## apps/poc/models.py

```python
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TimestampedModel, AuditedModel


class POCVersion(TimestampedModel, AuditedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    variant = models.ForeignKey('skus.Variant', on_delete=models.CASCADE, related_name='poc_versions')
    version_label = models.CharField(max_length=32)  # POC-v1, POC-v2
    printed_at = models.DateTimeField()
    printer = models.ForeignKey('manufacturing.Printer', on_delete=models.PROTECT)
    
    # Inputs từ slicer
    print_duration_minutes = models.IntegerField()
    filament_used_g = models.DecimalField(max_digits=8, decimal_places=2)
    filament_used_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    support_material_g = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    
    # Cost breakdown (VND)
    material_cost = models.DecimalField(max_digits=12, decimal_places=2)
    electricity_cost = models.DecimalField(max_digits=12, decimal_places=2)
    depreciation_cost = models.DecimalField(max_digits=12, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    postprocess_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    failure_buffer_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Pricing recommendation
    suggested_price = models.DecimalField(max_digits=12, decimal_places=2)
    markup_strategy = models.CharField(max_length=32, blank=True)
    
    notes = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)  # photo URLs, gcode key
    is_current = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'poc_versions'
        indexes = [
            models.Index(fields=['variant', 'is_current']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['variant'],
                condition=models.Q(is_current=True),
                name='uq_poc_one_current_per_variant',
            ),
        ]
```

## apps/ideas/models.py

```python
import uuid
from django.db import models
from apps.core.models import TimestampedModel, AuditedModel


class ProductIdea(TimestampedModel, AuditedModel):
    class Status(models.TextChoices):
        IDEA = 'idea'
        SKETCHING = 'sketching'
        POC = 'poc'
        VALIDATED = 'validated'
        IN_PRODUCTION = 'in_production'
        REJECTED = 'rejected'
        ON_HOLD = 'on_hold'
    
    class PipelineStage(models.TextChoices):
        CAPTURE = 'capture'
        RESEARCH = 'research'
        PROTOTYPE = 'prototype'
        TEST = 'test'
        LAUNCH = 'launch'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IDEA)
    pipeline_stage = models.CharField(max_length=16, choices=PipelineStage.choices, default=PipelineStage.CAPTURE)
    
    mood_board_assets = models.JSONField(default=list, blank=True)  # list of media_asset ids
    reference_links = models.JSONField(default=list, blank=True)  # [{url, title, source}]
    
    estimated_market_demand = models.CharField(
        max_length=8,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        blank=True,
    )
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_ideas')
    promoted_to_product = models.OneToOneField('catalog.Product', null=True, blank=True, on_delete=models.SET_NULL, related_name='source_idea')
    
    class Meta:
        db_table = 'ideas_product_ideas'
        indexes = [
            models.Index(fields=['status', 'pipeline_stage']),
            models.Index(fields=['assigned_to']),
        ]
```

## apps/channels/models.py

```python
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TimestampedModel


class MarketplaceCredential(TimestampedModel):
    class Channel(models.TextChoices):
        SHOPEE = 'shopee'
        LAZADA = 'lazada'
        TIKI = 'tiki'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    shop_id = models.CharField(max_length=64)
    access_token_encrypted = models.TextField()  # AES encrypted
    refresh_token_encrypted = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'channels_marketplace_credentials'
        unique_together = [('channel', 'shop_id')]


class ChannelListing(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft'
        SYNCING = 'syncing'
        SYNCED = 'synced'
        ERROR = 'error'
        DELETED = 'deleted'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    variant = models.ForeignKey('skus.Variant', on_delete=models.CASCADE, related_name='channel_listings')
    channel = models.CharField(max_length=16, choices=MarketplaceCredential.Channel.choices)
    shop_id = models.CharField(max_length=64)
    
    external_product_id = models.CharField(max_length=64, blank=True)
    external_sku_id = models.CharField(max_length=64, blank=True)
    external_seller_sku = models.CharField(max_length=64, blank=True)
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_override = models.IntegerField(null=True, blank=True)
    
    channel_attributes = models.JSONField(default=dict, blank=True)
    
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=32, blank=True)
    last_sync_error = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    
    class Meta:
        db_table = 'channels_channel_listings'
        unique_together = [('variant', 'channel', 'shop_id')]
        indexes = [
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['external_product_id']),
            models.Index(fields=['last_synced_at']),
        ]


class ProcessedEvent(models.Model):
    """Idempotency table cho marketplace webhooks."""
    id = models.BigAutoField(primary_key=True)
    source = models.CharField(max_length=16)  # shopee/lazada/tiki
    external_event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64, blank=True)
    payload = models.JSONField()
    processed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'channels_processed_events'
        unique_together = [('source', 'external_event_id')]
        indexes = [
            models.Index(fields=['processed_at']),
            models.Index(fields=['source', 'event_type']),
        ]
```

## apps/core/models.py

```python
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])


class AuditedModel(models.Model):
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL, related_name='+')
    updated_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL, related_name='+')
    class Meta:
        abstract = True


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=64, db_index=True)  # variant.created, license.changed
    entity_type = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    diff = models.JSONField(default=dict)  # JSON Patch RFC 6902
    metadata = models.JSONField(default=dict)  # ip, ua, request_id
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'core_audit_logs'


class DeadLetter(models.Model):
    id = models.BigAutoField(primary_key=True)
    task_name = models.CharField(max_length=128)
    payload = models.JSONField()
    error = models.TextField()
    traceback = models.TextField()
    attempt_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'core_dead_letters'


class MediaAsset(TimestampedModel):
    """Polymorphic media — gắn vào product hoặc variant hoặc design_file."""
    class Type(models.TextChoices):
        IMAGE = 'image'
        VIDEO = 'video'
        MODEL_3D = '3d_model'
        DOCUMENT = 'document'
    
    id = models.UUIDField(primary_key=True, default=models.UUIDField().default)
    owner_type = models.CharField(max_length=32)  # product | variant | design_file
    owner_id = models.CharField(max_length=64, db_index=True)
    
    type = models.CharField(max_length=16, choices=Type.choices)
    storage_key = models.CharField(max_length=512)
    cdn_url = models.URLField(blank=True)
    mime_type = models.CharField(max_length=64)
    size_bytes = models.BigIntegerField()
    
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    position = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'core_media_assets'
        indexes = [
            models.Index(fields=['owner_type', 'owner_id', 'position']),
        ]
```
