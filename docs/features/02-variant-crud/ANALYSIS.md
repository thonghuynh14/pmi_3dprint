# Feature Analysis: Variant CRUD (02-variant-crud)

## Summary
Variant = "phiên bản bán được" gắn với Product (combo material × color × size). v1 gồm CRUD đầy đủ + **Matrix bulk creator** + **SKU auto-gen theo BR-002**. Defer license/design_file/cost calc — sẽ làm khi Design Files & Material model ra.

## Problem Statement
**Pain**: Hiện chỉ có Product (catalog level). Không bán được gì vì sàn (Shopee/Lazada/Tiki) + POS đều yêu cầu SKU cụ thể (mỗi tổ hợp material+color+size là 1 SKU riêng). Catalog Manager phải tự ghi Excel mọi tổ hợp → trùng SKU, sai pattern BR-002, không sync giá/tồn được.

**Personas hưởng lợi v1**:
- **Catalog Manager** (chính): tạo variant matrix từ product, đặt base_price + cost_price
- **Designer**: set status `draft/active` (chưa có design_file FK v1)
- **Production Manager**: nhập cost_price tay (cost calc tự động defer)
- **Channel Operator**, **Cashier**: chưa hưởng lợi v1 — chờ channel sync + POS

**Bằng chứng**: full-spec.md (section Variant/SKU), business-rules.md (BR-001/002/009). Không có user interview cụ thể beyond spec — quyết định dựa trên spec gốc đã agreed.

## MVP Alignment
- [x] Trong MVP scope — Variant là core PIM, "không có không bán được"
- [x] Aligns primary goal "quản lý sản phẩm + SKU in 3D đa kênh"
- [x] Dependency Product CRUD đã có (commit `91ddf64` + `c14c9f1`)
- [x] Không conflict "Out of Scope" trong PRD

## Decisions từ PHA 1 (4 câu gate)

| # | Quyết định | Lý do |
|---|---|---|
| 1 | **Single form + Matrix bulk** | Matrix là killer feature 3D PIM — tạo 50 variant/product là chuyện thường |
| 2 | **3 axis: material + color + size_preset** | Bao ~80% case thật; layer_res + infill là print setting → đẩy JSON attributes |
| 3 | **Auto-gen SKU theo BR-002** | Đúng business rule; user không cần nhớ pattern; cần `select_for_update` chống race |
| 4 | **Defer license + design_file + cost calc** | Scope sạch; BR-003 chờ Design Files; BR-005 chờ Material model |

## Impact
- **Reach**: ~5/6 role (Catalog Manager, Designer, Production Manager dùng ngay; Channel Operator + Cashier chờ feature sau)
- **Importance**: **Critical** — chặn mọi feature downstream (channel sync, POS, inventory)
- **Confidence**: **High** — spec rõ, pattern Product CRUD đã verified

## Effort estimate (L ~ 21h)

| Mảng | Giờ |
|---|---|
| BE: model + migration (3 axis + sequence) + selector | 3h |
| BE: service `variant_create` với `select_for_update` chống race, `variant_bulk_create_matrix` | 4h |
| BE: viewset + serializers (input/output/matrix-input) + filter + audit log | 3h |
| BE: tests (race, SKU pattern BR-002, matrix cap, dup detection) | 3h |
| FE: list + single form CRUD (giống pattern Product) | 4h |
| FE: matrix UI (chips chọn axis values + preview table + bulk submit) | 4h |
| FE: tests (zod, hook, e2e matrix flow) | 2h |
| **Total** | **~23h (L)** |

So với Product CRUD (~12h): **+90%** vì matrix UI + sequence race protection + 1 entity (Product) tham chiếu thêm.

## Alternatives considered
| Cách khác | Lý do REJECT |
|---|---|
| JSON attributes trên Product, không có Variant table | Không filter/index per-axis được; không auto-gen SKU per combination; không lưu price/stock per-variant |
| Single CRUD, bỏ matrix khỏi v1 | Mất giá trị 3D-specific — tạo 50 variant/product 1 form = không xuể, vi phạm requirement core |
| Manual SKU only | Vi phạm BR-002 dễ, user phải hiểu pattern, error rate cao |
| FK Material model ngay v1 | Material chưa có → phải build Material trước = scope creep; v1 dùng string `material_name` + `material_code3` |

## Risks
- **R1 — Race condition sequence number** 🔴 Critical  
  2 user tạo variant cùng Product đồng thời → trùng `NN`.  
  → Mitigation: `select_for_update()` trên Product khi gen next sequence; test concurrent insert (5 thread → 5 SKU unique).
- **R2 — Variant explosion** 🟠 Major  
  Matrix 10×10×10 = 1000 variants/lần → DB stress + UI freeze.  
  → Mitigation: cap **100 variant/batch** ở serializer; FE warning toast khi N×M×P > 50.
- **R3 — Matrix UI state complexity** 🟠 Major  
  Quản lý NxM grid + validate trước submit là FE work nặng.  
  → Mitigation: v1.0 matrix chỉ generate (preview-then-confirm, không edit per-cell); v1.1 cho edit cell sau.
- **R4 — SKU pattern thiếu CAT3** 🟡 Minor (OQ-1)  
  BR-002 cần `[CAT3]` từ Category, chưa có Category feature.  
  → Decision pending PHA 2: dùng pattern `<sku_root>-<MAT3>-<COLOR3>-<SIZE>-<NN>` length 12-22 (vẫn trong BR-002 range 12-24); migrate add CAT3 khi Category ra.
- **R5 — MAT3/COLOR3 từ string** 🟡 Minor (OQ-2)  
  User nhập "Polylactic Acid Red" → MAT3 = ?  
  → Decision pending PHA 2: form 2 field (name + code3); validate code3 = uppercase alphanumeric 2-4 chars.

## Open Questions (resolve ở PHA 2)
- **OQ-1**: SKU pattern v1 với hay không có CAT3? → Đề xuất WITHOUT (ghi chú migrate sau).
- **OQ-2**: Material/Color code3 nhập tay hay auto-derive từ name?
- **OQ-3**: Variant status enum — `draft/active/archived` giống Product, hay thêm `inactive`?
- **OQ-4**: Variant `name` field — auto-sinh từ "{product.name} {color} {size}" hay cho user override?
- **OQ-5**: Soft delete + restore + audit log — copy pattern Product luôn?
- **OQ-6**: Matrix UI — chỉ generate (preview-then-confirm) hay cho edit từng cell trước submit?
- **OQ-7**: Allow tạo variant trên Product status `archived`? → đề xuất KHÔNG.

## Success metric
- API `POST /variants/` p95 < 500ms (single), < 2s (matrix 50 variants)
- BE test coverage ≥ 80% (target 90%+, theo precedent Product 97%)
- Race condition test pass: 5 thread tạo đồng thời → 5 SKU unique, không IntegrityError
- E2E Playwright: tạo product → matrix 2×3 → 6 variants xuất hiện trong list → đúng SKU pattern
- Manual: tạo 50 variants/product trong < 1 phút (vs Excel hiện tại ~10 phút)

## Recommendation

# 🟢 BUILD NOW

**Reasoning**:
- MVP alignment cao nhất trong roadmap còn lại — variant là core domain, chặn mọi feature downstream.
- Scope đã khoanh gọn qua 4 câu gate (bỏ license/design_file/cost calc).
- Effort 23h (L) — không phải XL.
- Pattern pipeline đã verified với Product CRUD (skill chain trơn tru).
- Risk lớn nhất (race + matrix UI) có mitigation cụ thể.

## Next steps
→ Sau khi user confirm 🟢 BUILD NOW:
1. **PHA 2 `ba-spec`** — resolve 7 OQ ở trên + viết `SPEC.md` / `DESIGN.md` / `TASKS.md`
2. Handoff `db-schema` — Variant model + migration (partial unique + indexes)
3. Handoff `django-backend` — service với `select_for_update`, viewset, matrix endpoint
4. Handoff `nextjs-frontend` — list, single form, matrix UI
5. Handoff `test-generator` — race condition + matrix tests
6. `code-review` → 2 commit (BE + FE, giống pattern Product `91ddf64` + `c14c9f1`)

→ Nếu user muốn **SIMPLIFY (🟠)**: bỏ matrix bulk khỏi v1 → effort xuống ~13h, nhưng mất giá trị 3D-specific.

→ Nếu **BUILD LATER (🟡)**: vào backlog. Nhưng đây là feature lõi MVP → khó né lâu.
