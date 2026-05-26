# Full Spec - 3D Printing PIM

> ⚠️ **PLACEHOLDER** — File này cần được điền nội dung từ artifact spec gốc đã được Claude research trước đó.
>
> **Action cần làm**:
> 1. Mở artifact: "Product and SKU Management System for 3D Printing Multi-Channel Sales: Technical Specification" trong conversation gốc với Claude
> 2. Copy toàn bộ nội dung markdown của artifact đó
> 3. Paste vào file này (thay thế nội dung placeholder hiện tại)
> 4. Commit: `git add docs/architecture/full-spec.md && git commit -m "docs(architecture): add original spec"`

---

## Tóm tắt nhanh (để skills reference khi chưa có nội dung đầy đủ)

### Domain
Hệ thống quản lý SKU + đa kênh cho doanh nghiệp in 3D, bán Shopee/Lazada/Tiki + POS offline.

### Stack đã chốt
- Backend: Django 5 + DRF + PostgreSQL 16 (Supabase) + Celery + Redis
- Frontend: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- Auth: Django (Pattern A — không dùng Supabase Auth)

### Data model 3 tầng
```
Product → Variant → ChannelListing
   ↑          ↑              ↑
attributes  axes(5)    per-marketplace
(JSONB)    (M×C×S×L×I)   (Shopee/Lazada/Tiki)
```

### Đặc thù 3D printing
- File STL có versioning, license CC0/CC BY/CC BY-NC/...
- BOM theo gram filament (không phải piece)
- Variant axes: material × color × size × layer_resolution × infill (5 trục)
- Printer compatibility: máy nào in được variant nào
- POC = Proof of Concept print → cost breakdown (material + electricity + depreciation + labor + buffer)

### Marketplace constraints
- **Shopee**: HMAC-SHA256 sign, token TTL 4h, max 50 variants/stock call, 2 tier_variations
- **Lazada**: OAuth + signed XML, token TTL 7d, SPU/Product/SKU hierarchy
- **Tiki**: OAuth 2.0, **HARD LIMIT 2 option_attributes**

### SKU pattern
`[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]` — length 12-24, chars [A-Z0-9-]

### Business rules
Xem [business-rules.md](business-rules.md) cho BR-001 → BR-010.

### Schema overview
20+ bảng tổ chức theo Django apps:
- `accounts` (User + RBAC)
- `catalog` (Brand, Category với ltree, Product, AttributeDefinition)
- `skus` (Variant, SkuCode)
- `design_files` (DesignFile với versioning + license enum)
- `materials` (Material master + Supplier)
- `manufacturing` (Printer, BOM, BOMLine, VariantCompatiblePrinter)
- `poc` (POCVersion với unique current per variant)
- `ideas` (ProductIdea pipeline)
- `channels` (MarketplaceCredential encrypted, ChannelListing, ProcessedEvent)
- `core` (TimestampedModel, SoftDeleteModel, AuditLog, DeadLetter, MediaAsset)

Xem `[.claude/skills/db-schema/references/full_schema.md](../../.claude/skills/db-schema/references/full_schema.md)` cho định nghĩa đầy đủ Django models.

### Phasing (3 phase MVP, 3 tháng)

**Phase 1 (M1-M3)**: Catalog + SKU + Design Files + Materials + BOM + Printers + POC + Auth + RBAC + Shopee sync + Audit log

**Phase 2 (M4-M5)**: Lazada + Tiki sync, 3D preview, Ideas pipeline

**Phase 3 (M6)**: POS offline, mobile responsive

### Defaults VN
- Điện EVN: ~3000 VND/kWh
- PLA filament: 350-500K VND/kg
- FDM printer lifetime: 5000-10000h
- GS1 VN prefix: 893 (~1M VND đăng ký + 500K/năm cho 10-digit), effective 1/1/2026

### Cost formula (BR-005)
```
total_cost = material + electricity + depreciation + labor + postprocess + failure_buffer(10%)
suggested_price = total_cost × 2.5 (markup default)
```

---

## TODO

Thay thế nội dung file này bằng spec đầy đủ từ artifact gốc. Đó là tài liệu single source of truth dài ~30-50 trang chứa:

- Use case detail cho từng module
- API design chi tiết
- Frontend pages + components breakdown
- Migration strategy nếu có data Excel cũ
- Error handling patterns
- Monitoring + alerting
- Security policies
- Pitfalls + best practices
- Tham khảo Akeneo PIM, MOSS, Shopify Plus pattern
