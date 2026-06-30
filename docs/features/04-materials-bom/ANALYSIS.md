# Feature Analysis: Materials / BOM / Cost (Full scope)

## Summary

Master data nguyên vật liệu (filament/resin/phụ kiện) + công thức BOM (recipe gram-per-variant) + wire BR-005 auto-calculate `cost_price` cho variant từ BOM × giá NVL + điện + khấu hao + nhân công + buffer.

## Problem Statement

Hiện tại:
- **Variant.material_name/code3** chỉ là chuỗi text rời rạc; mỗi variant nhập tay, không tracking inventory.
- **`Variant.cost_price`** field tồn tại nhưng `null` ở 18/18 variant đã seed — user phải nhập tay, không có công thức.
- **BR-005** đã ghi vào business-rules.md nhưng chưa wire code → margin tính tay trên Excel, hay sai.

**Persona pain (từ personas.md):**
- **Chị Lan (Production Manager)**: 35 tuổi, kỹ sư cơ khí, quản lý xưởng 10 máy in 3D. Goal: "biết chính xác cần mua bao nhiêu kg PLA Red cho batch order tuần này". Pain: track filament tồn kho bằng giấy, hay quên định lượng. → Cần Materials master + tồn kho realtime.
- **Anh Hùng (Catalog Manager)**: tạo variant không thấy margin → set giá bán tuỳ ý → có thể lỗ. → Cần auto cost_price từ BOM để biết margin.

→ Không gỡ blocker này thì: (1) feature POC sau không có cost target để chạm; (2) channel publish không biết margin để pricing; (3) report tồn kho impossible.

## MVP Alignment

- [x] In MVP scope — Materials/BOM/POC nằm trong PRD modules list từ đầu
- [x] Aligns với primary goal (internal tool quản lý SKU end-to-end gồm cost)
- [x] Không conflict với "Out of Scope" — đã chốt full ERP-lite, không phải full accounting/ERP

## Impact

- **Reach**: 100% Production Manager + 80% Catalog Manager (cần xem cost). Foundational cho POC + Channel pricing.
- **Importance**: **Critical** (blocker cho POC + cost-based pricing)
- **Confidence**: **High** — persona đã có pain cụ thể, BR-005 đã spec, cost formula đã chốt với env defaults sẵn (`ELECTRICITY_PRICE_VND_PER_KWH=3000`, `DEFAULT_LABOR_RATE_VND_PER_HOUR=50000`, `DEFAULT_FAILURE_BUFFER_PERCENT=10`)

## Scope (Full cut, đã chốt với user)

### Trong scope ✅

#### Materials master
1. `apps/materials` app với `Material` model: code (PLA, PETG, ABS-RED…), name, type (filament/resin/phụ kiện), subtype (pla/petg/abs/pla+/wood-pla), color, color_code3 (cho SKU), price_per_unit (Decimal), unit (g/ml/piece), stock_quantity, density_g_cm3 (cho tính khối lượng từ volume), supplier (nullable), is_active.
2. CRUD endpoints: list/retrieve/create/partial_update/destroy + soft delete + restore.
3. Permission: `material:manage` (Production Manager + Super Admin).
4. Django Admin: list filter theo type/subtype, bulk import CSV defer.
5. Stock adjustment endpoint: POST `/materials/<id>/adjust/` với reason (purchase/usage/waste/correction) → ghi `MaterialStockLog`.

#### BOM (Recipe)
6. `BOM` model: 1:1 với Variant, `is_active=True` flag (1 active per variant qua partial unique).
7. `BomLine` model: BOM × Material × quantity_grams + waste_percent (mặc định 10% = BR-005 failure_buffer).
8. `bom_create_from_template` service: nhận `{variant_id, lines: [{material_id, grams}], waste_percent}` → tạo BOM + lines atomic.
9. Endpoint: GET/POST/PATCH `/skus/variants/<id>/bom/` nested resource.

#### Cost calculation (BR-005)
10. `cost_compute_variant(variant)` service: trả `{material_cost, electricity_cost, depreciation_cost, labor_cost, failure_buffer, total}` Decimal precision.
11. **Trigger auto-recalc** `Variant.cost_price` khi:
    - BOM line thêm/sửa/xoá
    - Material `price_per_unit` đổi (signal `post_save`)
    - Variant `weight_g` đổi
12. Lock prevent recursive update (Variant.save → ko trigger BOM signal lại).
13. **Đầu vào cho cost formula** (tạm hardcode trong service, configurable qua env như đã thiết lập trước):
    - Material: `BOMLine.material.price_per_unit × BomLine.quantity_grams × (1 + waste_percent/100)`
    - Electricity: `kwh_per_hour=0.15` × `print_hours` (lấy từ `Variant.lead_time_hours` nếu có, default 0) × `ELECTRICITY_PRICE_VND_PER_KWH`
    - Depreciation: defer (cần Printer model — feature sau). Tạm 0.
    - Labor: `print_hours × DEFAULT_LABOR_RATE_VND_PER_HOUR / 60` (per-minute)
    - Failure buffer: tổng × `DEFAULT_FAILURE_BUFFER_PERCENT/100`
14. **Cost không lưu breakdown** — chỉ lưu `total` vào `Variant.cost_price`; breakdown trả về qua API on-demand (cho UI hiển thị "Tại sao cost = X").

#### FE
15. Materials admin page: list + search + filter theo type + edit form.
16. Material detail có history stock adjustment.
17. BOM editor inline ở Variant detail (Production Manager only): add/remove/edit BomLine + hiển thị cost breakdown realtime.
18. Cost breakdown panel ở Variant detail (mở rộng được, dạng accordion).

### Out of scope ❌ (defer)
- **Bulk import CSV materials** (nhập tay 20-30 vật liệu OK, defer bulk khi cần > 100)
- **Multi-currency** (chỉ VND, BR-005 spec)
- **Material lot tracking** (FIFO/LIFO valuation) — defer khi cần accounting
- **Printer model + depreciation auto** — defer feature `printers`
- **POC version + actual print log** — defer feature `poc`
- **Auto reorder threshold + supplier integration** — defer
- **Material allergen / safety data sheet** — defer
- **Recipe versioning history** (chỉ giữ active BOM, không track v1/v2/v3 BOM) — defer

## Effort estimate

| Layer | Effort | Detail |
|---|---|---|
| BE — Material model + CRUD + stock log | 8h | model + service + viewset + admin + tests |
| BE — BOM + BomLine + nested endpoint | 6h | 2 models + service + nested API + atomic create |
| BE — Cost calc service + signals + recalc | 6h | BR-005 formula + signal post_save + recursive lock |
| BE — Tests (model + service + viewset + signals + cost matrix) | 5h | parametrize cost cases |
| FE — Materials admin (list + form + stock adjust) | 6h | TanStack table + form RHF + zod + stock log table |
| FE — BOM editor inline + cost breakdown panel | 4h | dynamic line array + accordion |
| FE — Tests (zod + hooks via MSW) | 2h | |
| Docs + ADR + business-rules | 1h | append BR-015 (BOM 1-active), BR-016 (waste %), ADR cost-calc decisions |
| **Total** | **~38h** | **L/XL effort** (~4-5 ngày dev) |

## Alternatives considered

- **Option A — Materials CRUD only** (rejected): user explicitly chose Full. CRUD-only không gỡ pain pricing/margin, defer cost vẫn phải làm sau → đẩy nợ.
- **Option B — Defer BOM, làm pos-app trước** (rejected): POS cần cost để in tem có giá; pricing không có cost = không bán được offline.
- **Option C — BOM dạng JSON field không bảng riêng** (rejected): query "tất cả variant dùng PLA Red" sẽ phải full-scan JSON, không indexable. Khi production scale lên 500 variant sẽ chậm.
- **Option D — Cost lưu breakdown vào DB** (rejected): formula còn thay đổi (vd thêm Printer depreciation sau), breakdown stale nhanh. Recompute on-demand sạch hơn.
- **Option E — Replace Variant.material_name/code3 bằng FK ngay** (rejected ở MVP này): yêu cầu data migrate 18 variant existing + đổi shape JSON axes. Để feature 05 (refactor variant axes) khi cần real-time stock từ Material model. Hiện chỉ link BOM.material → Material, KHÔNG đụng axes.

## Risks

1. **Cost recalc storm**: đổi giá `Material.price_per_unit` → trigger recalc cho mọi `BomLine` reference → mọi `Variant.cost_price`. Nếu 1 material dùng cho 500 variant → 500 UPDATE.
   - **Mitigation**: Celery task async `materials.tasks.recompute_variant_costs(material_id)` + Material model thêm flag `is_recomputing` để chống concurrent.
2. **Signal recursive**: `Variant.save()` không được trigger BOM signal lại.
   - **Mitigation**: dùng `Variant.objects.filter(pk=...).update(cost_price=...)` (skip save signal) thay vì `variant.save()`.
3. **Decimal precision drift**: floating point vs Decimal khi chia / nhân waste_percent.
   - **Mitigation**: dùng `Decimal` xuyên suốt service, quantize 2dp ở output.
4. **BOM 1-active per variant**: phải có constraint `UniqueConstraint(variant, is_active=True)` partial.
   - **Mitigation**: PostgreSQL partial unique index `WHERE is_active = true AND deleted_at IS NULL`.
5. **Material soft-delete khi đang dùng**: Material đang có BomLine reference, soft-delete sẽ orphan recipe → cost calc fail.
   - **Mitigation**: chặn soft-delete nếu còn BomLine alive (raise `MaterialInUseError`), hoặc archive thay vì delete.
6. **Existing variant không có BOM**: 18 variant đã seed chưa có BOM. Cost = null. UI cần handle "no BOM" state, KHÔNG break list.
   - **Mitigation**: cost_price nullable (đã có), UI hiển thị "Chưa thiết lập BOM" với CTA "Tạo BOM".

## Recommendation

**🟢 BUILD NOW**

**Reasoning**:
- Critical importance (blocker cho POC + cost-based pricing + report tồn kho).
- Reach 100% Production Manager + 80% Catalog Manager.
- BR-005 đã spec với env defaults sẵn → không phải design lại công thức.
- Persona pain rõ ràng từ personas.md.
- Effort L/XL (~38h) hợp lý cho impact strategic.
- Risk lớn nhất (recalc storm) controllable qua Celery + lock flag.

## Next steps

→ **Đợi user confirm "build now"** trước khi vào PHA 2 (SPEC/DESIGN/TASKS)

PHA 2 sẽ chốt:
- Field detail của Material (đặc biệt density, supplier shape)
- BOM line: chỉ material + grams + waste_percent, hay thêm note/version?
- Cost formula precision: round mỗi step hay round chỉ ở total?
- Permission split: `material:manage` vs `bom:edit` vs `cost:view` (hiện chỉ 1 perm — có cần tách?)
- Stock log granularity: mỗi adjust 1 row, hay aggregate daily?
- Material code: free-form vs constrained (vd PLA, PLA-RED, PLA-RED-PRUSAMENT)?
