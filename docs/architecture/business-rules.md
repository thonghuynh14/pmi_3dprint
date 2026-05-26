# Business Rules

> Các business rules quan trọng, được reference xuyên suốt code (comments, exceptions, tests).
> Khi thêm rule mới → append vào đây + update skills nếu cần.

## BR-001: SKU uniqueness

**Rule**: SKU phải unique trên toàn hệ thống, không phân biệt case (uppercase vs lowercase được coi là trùng).

**Why**: SKU là mã định danh duy nhất cho 1 variant. Trùng → ambiguous khi push lên marketplace, sai khi POS scan barcode.

**Enforcement**:
- DB level: `unique=True` trên `Variant.sku` field
- Service: `generate_sku()` dùng `SELECT FOR UPDATE` chống race condition
- Migration: convert tất cả SKU sang uppercase trước khi add unique constraint

**Exception**: `SkuConflictError(409)` khi attempt insert duplicate

**Test**: `test_concurrent_creation_no_sku_collision`

---

## BR-002: SKU pattern

**Rule**: SKU phải match pattern `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`, tổng độ dài 12-24 ký tự, chỉ chấp nhận `[A-Z0-9-]`.

**Format**:
- `CAT3`: 3-char category code (FIG, GDT, JWL, ...)
- `PROD6`: 6-char product code (slug compact uppercase)
- `MAT3`: 3-char material code (PLA, ABS, RES, ...)
- `COLOR3`: 3-char color code (RED, BLU, BLK, ...) — optional nếu single color
- `SIZE`: 1-6 char size (S, M, L, IP15, IP15PM, ...) — optional
- `NN`: 2-digit sequence (01-99)

**Examples**:
- `FIG-DRAGON-PLA-RED-M-01` ✅ (length 22)
- `GDT-PHCASE-TPU-BLK-IP15-01` ✅ (length 25 — too long!)
- `JWL-RING-RES-CLR-7-01` ✅ (length 20)

**Why**: Pattern cho phép parse SKU human-readable. POS staff có thể đọc SKU và đoán product/variant.

**Enforcement**:
- `generate_sku()` validate regex sau khi build
- Check length 12-24 inclusive

**Exception**: `ValueError` if generated SKU không match

**Test**: `test_sku_length_in_range_12_to_24`, `test_only_allowed_chars`

---

## BR-003: License blocks commercial use

**Rule**: Variant không thể chuyển sang `status='active'` nếu attached design file có `license_allows_commercial = False`.

**Affected licenses**:
- ❌ CC BY-NC, CC BY-NC-SA, CC BY-NC-ND → NC = NonCommercial = not allowed
- ✅ CC0, CC BY, CC BY-SA, CC BY-ND → allowed
- ⚠️ All Rights Reserved → check contract case-by-case

**Why**: Bán SP với file CC BY-NC = vi phạm license → lawsuit risk.

**Enforcement**:
- Service `variant_create` / `variant_update` validate trước khi save
- DesignFile.save() derive `license_allows_commercial` từ `license_type`

**Exception**: `LicenseCommercialBlockError(400)` với `error_code='LICENSE_BLOCKS_COMMERCIAL'`

**Special case**: Đổi license của design file sau khi variant đã active → trigger reactive validation, có thể cần unpublish variant.

**Test**: `test_blocks_when_license_disallows_commercial`, `test_allows_draft_status_with_nc_license`

---

## BR-004: Tiki max 2 option attributes

**Rule**: Khi push variant lên Tiki, product không thể có > 2 option_attributes active. Nếu vi phạm, block + suggest merge axes.

**Why**: Tiki Open API limit cứng. Cố push 3+ axes → API trả lỗi.

**Enforcement**:
- `TikiConnector.create_product` check `len(active_axes)` trước khi build payload
- UI hiển thị warning sớm khi user setup 3+ axes mà có Tiki listing

**Suggested merges**:
- `color + size + material` → merge thành `color + variant_label` (variant_label = "PLA-M")
- `material + color + layer_res` → merge `color + spec` (spec = "RED-0.2mm")

**Exception**: `TikiOptionAttributesExceededError(400)` với `error_code='TIKI_OPTION_LIMIT'`

**Test**: `test_blocks_when_3_axes`, `test_allows_2_axes`

---

## BR-005: POC cost formula

**Rule**: Cost cho 1 POC version = material + electricity + depreciation + labor + post-process + failure_buffer.

**Formula** (VND):
```
material_cost      = filament_used_g × material.price_per_unit
electricity_cost   = (print_duration_minutes/60) × (printer.wattage_kw) × 3000  # VND/kWh EVN avg
depreciation_cost  = (print_duration_minutes/60) × (printer.purchase_price / printer.lifetime_hours)
labor_cost         = labor_minutes × (hourly_rate / 60)
postprocess_cost   = manual input (sanding, painting, packaging)
failure_buffer     = (sum_above) × (printer.failure_rate / 100)  # default 10%

total_cost = material + electricity + depreciation + labor + postprocess + failure_buffer
```

**Suggested selling price**:
```
suggested_price = total_cost × markup_multiplier  # default 2.5x
```

**Why**: Track full cost = biết margin thật. Bỏ qua depreciation = ảo tưởng lãi.

**Enforcement**:
- Service `poc_create` tự tính các thành phần
- Save vào POCVersion fields riêng cho audit

**Test**: `test_poc_cost_calculation_matches_formula`

---

## BR-006: Stock sync timing

**Rule**: Khi master stock thay đổi (do POS, do order online), tất cả channel listings phải sync stock < 30 giây.

**Why**: Race condition giữa 2 buyers trên 2 sàn → overselling.

**Enforcement**:
- Master stock change trigger Celery `stock_sync_fanout.delay(variant_id, new_stock)`
- Fan-out gọi `push_stock_to_shopee/lazada/tiki.delay()` parallel
- Mỗi task có `soft_time_limit=25s`
- Monitor: alert nếu p95 latency > 30s

**SLA**: 95% updates complete trong 30s, 100% trong 5 phút.

**Test**: Integration test với mock marketplace API + measure timing.

---

## BR-007: Safety stock buffer

**Rule**: Mỗi channel listing có safety_stock_percent default 5-10% (configurable). Stock push lên kênh = master_stock × (1 - safety_percent/100).

**Why**: Chống overselling do sync delay. Vd master = 100, safety 5% → push 95 lên kênh.

**Enforcement**:
- `ChannelListing.safety_stock_percent` field, default 5
- Service `_compute_pushable_stock()` tính trước khi push
- POS không apply safety (đếm chính xác stock vật lý)

**Override**: Channel Operator có thể set per-listing (vd Tiki rủi ro hơn → 10%)

---

## BR-008: STL preview requirement

**Rule**: File STL > 100MB phải có GLB preview generated trước khi gắn variant `active`. File STL nhỏ hơn → optional nhưng recommended.

**Why**:
- File lớn → web viewer load chậm
- GLB tối ưu cho web (compressed, fast)
- Customer experience trên Shopee preview

**Enforcement**:
- Service `variant_promote_to_active` check `design_file.glb_preview_key`
- Celery task `convert_stl_to_glb` chạy ngay khi upload STL > 100MB
- Block activate nếu preview chưa ready

**Test**: `test_active_status_requires_glb_for_large_stl`

---

## BR-009: Audit log for state changes

**Rule**: Mọi thay đổi state quan trọng phải tạo `AuditLog` entry với actor + diff + timestamp.

**Required audit events**:
- `variant.created`, `variant.status_changed`, `variant.price_changed`
- `design_file.license_changed`
- `channel_listing.published`, `channel_listing.unpublished`
- `poc.created`, `poc.current_changed`
- `user.role_changed`
- `material.price_changed`
- Stock changes (bulk + individual)

**Format**:
```python
AuditLog(
    actor=user,
    action='variant.created',
    entity_type='Variant',
    entity_id=str(variant.id),
    diff={'sku': 'FIG-001-01', 'base_price': '150000'},
    metadata={'ip': '1.2.3.4', 'user_agent': '...', 'request_id': '...'},
)
```

**Why**:
- Truy vết khi có dispute (ai đổi giá, khi nào)
- Forensic khi data corrupt
- Compliance (audit trail)

**Retention**: Giữ 2 năm minimum, có thể partition by month sau khi > 10M rows.

**Enforcement**: Service layer call `audit_log()` sau mỗi state change. Reviewer check trong code-review.

---

## BR-010: Internal barcode prefix

**Rule**: Barcode internal dùng EAN-13 với prefix `020-029` (internal use, restricted distribution). KHÔNG dùng prefix `893` (Vietnam GS1) trừ khi đã đăng ký với GS1 VN.

**Format EAN-13**: `[2-3 digit prefix][9-10 digit product code][1 check digit]`

**Examples**:
- `0201234567890` ✅ (internal use, OK cho POS nội bộ)
- `8931234567890` ⚠️ chỉ khi có GS1 VN license (~1M VND/năm)

**Why**:
- Prefix 020-029 reserved cho internal store use (UPC-E standard)
- Prefix 893 là Vietnam GS1 — cần đăng ký, có effective 1/1/2026 theo vnpc.gs1.gov.vn

**Enforcement**:
- Default barcode generator dùng prefix `020`
- Setting `BARCODE_PREFIX` configurable
- Validation: nếu prefix `893` thì check `GS1_LICENSE_ACTIVE = True`

**Test**: `test_default_barcode_uses_internal_prefix`

---

## Adding new business rules

Khi phát hiện rule mới trong quá trình dev:

1. Add ở đây với format trên (Rule + Why + Enforcement + Exception + Test)
2. Reference trong skill `ba-spec/SKILL.md` (section "Business rules library")
3. Tạo exception class trong `apps/core/exceptions.py`
4. Add test case `test_<br_id>_*`
5. Update `CLAUDE.md` summary
