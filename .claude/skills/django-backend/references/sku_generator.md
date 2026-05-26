# SKU Generator Logic

## Pattern
```
[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]
```

Examples:
- `FIG-DRAGON-PLA-RED-M-01`
- `GDT-PHCASE-TPU-BLK-IP15-01`
- `JWL-RING-RES-CLR-7-01`

## Implementation

```python
# apps/skus/utils/sku_generator.py
import re
from typing import TypedDict
from django.db import transaction
from apps.catalog.models import Product, Category
from apps.materials.models import Material
from apps.skus.models import Variant, SkuCode


class VariantAxes(TypedDict, total=False):
    material_id: str
    material_color: str
    size_preset: str
    layer_resolution_mm: float
    infill_percent: int


def _slug_compact(text: str, max_len: int = 6) -> str:
    """Convert text → compact uppercase code, max 6 chars."""
    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
    return cleaned[:max_len]


def _get_code(entity_type: str, value: str, default: str | None = None) -> str:
    """Lookup short code from sku_codes table. Fallback to first 3 chars."""
    if not value:
        return ''
    try:
        return SkuCode.objects.get(entity_type=entity_type, value__iexact=value).code
    except SkuCode.DoesNotExist:
        return default or _slug_compact(value, max_len=3)


@transaction.atomic
def generate_sku(*, product_id: str, axes: VariantAxes) -> str:
    """Generate next SKU for a product + axes combination.
    
    Uses SELECT FOR UPDATE on Product to serialize sequence generation.
    """
    product = Product.objects.select_for_update().select_related('primary_category').get(id=product_id)
    
    # Build parts
    cat_code = product.primary_category.code_3 if product.primary_category else 'GEN'
    prod_code = _slug_compact(product.name, max_len=6)
    
    mat_code = ''
    if axes.get('material_id'):
        mat = Material.objects.get(id=axes['material_id'])
        mat_code = mat.code
    
    color_code = _get_code('color', axes.get('material_color', ''))
    size_code = axes.get('size_preset', '').upper()[:6]
    
    # Sequence: count existing variants of this product + axes signature
    base = '-'.join(filter(None, [cat_code, prod_code, mat_code, color_code, size_code]))
    
    # Find next sequence
    existing = Variant.objects.filter(
        sku__startswith=f"{base}-"
    ).values_list('sku', flat=True)
    
    used_seqs = set()
    for sku in existing:
        match = re.match(rf'^{re.escape(base)}-(\d{{2}})$', sku)
        if match:
            used_seqs.add(int(match.group(1)))
    
    next_seq = 1
    while next_seq in used_seqs:
        next_seq += 1
    
    if next_seq > 99:
        raise ValueError(f"Sequence exhausted for base SKU {base}")
    
    sku = f"{base}-{next_seq:02d}"
    
    # Validate length 12-24 (BR-002)
    if not (12 <= len(sku) <= 24):
        raise ValueError(f"Generated SKU '{sku}' length {len(sku)} out of range 12-24")
    
    if not re.match(r'^[A-Z0-9\-]+$', sku):
        raise ValueError(f"Generated SKU '{sku}' contains invalid chars")
    
    return sku
```

## SkuCode model (abbreviation library)

```python
# apps/skus/models/sku_code.py
class SkuCode(models.Model):
    """Mapping entity values → short codes for SKU generation.
    
    Examples:
    - entity_type='color', value='Royal Blue', code='RBL'
    - entity_type='material', value='PLA Plus', code='PLP'
    - entity_type='size', value='Small', code='S'
    """
    entity_type = models.CharField(max_length=32)  # color, material, size, category
    value = models.CharField(max_length=64)
    code = models.CharField(max_length=8)
    
    class Meta:
        unique_together = [('entity_type', 'value'), ('entity_type', 'code')]
```

## Tests cần có

```python
# apps/skus/tests/test_sku_generator.py
import pytest
from apps.skus.utils.sku_generator import generate_sku

@pytest.mark.django_db
class TestGenerateSku:
    def test_first_variant_gets_seq_01(self, product, axes_pla_red_m):
        sku = generate_sku(product_id=product.id, axes=axes_pla_red_m)
        assert sku.endswith('-01')
    
    def test_sequence_increments(self, product, variant_factory, axes_pla_red_m):
        variant_factory(product=product, sku='FIG-DRAGON-PLA-RED-M-01')
        sku = generate_sku(product_id=product.id, axes=axes_pla_red_m)
        assert sku.endswith('-02')
    
    def test_fills_gap_in_sequence(self, product, variant_factory, axes_pla_red_m):
        variant_factory(product=product, sku='FIG-DRAGON-PLA-RED-M-01')
        variant_factory(product=product, sku='FIG-DRAGON-PLA-RED-M-03')
        sku = generate_sku(product_id=product.id, axes=axes_pla_red_m)
        assert sku.endswith('-02')
    
    def test_length_within_range(self, product, axes_pla_red_m):
        sku = generate_sku(product_id=product.id, axes=axes_pla_red_m)
        assert 12 <= len(sku) <= 24
    
    def test_only_allowed_chars(self, product, axes_pla_red_m):
        import re
        sku = generate_sku(product_id=product.id, axes=axes_pla_red_m)
        assert re.match(r'^[A-Z0-9\-]+$', sku)
    
    def test_sequence_exhausted_raises(self, product, variant_factory, axes_pla_red_m):
        for i in range(1, 100):
            variant_factory(product=product, sku=f'FIG-DRAGON-PLA-RED-M-{i:02d}')
        with pytest.raises(ValueError, match='Sequence exhausted'):
            generate_sku(product_id=product.id, axes=axes_pla_red_m)
    
    def test_concurrent_generation_no_collision(self, product, axes_pla_red_m, db_transaction):
        """SELECT FOR UPDATE phải serialize 2 transaction đồng thời."""
        # Use threading + transaction.atomic to test
        ...
```
