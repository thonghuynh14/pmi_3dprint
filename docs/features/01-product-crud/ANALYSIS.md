# Feature Analysis: CRUD Product

> Output từ skill `ba-spec` PHA 1. Mục đích: gate trước khi build.

## Summary
CRUD Product cơ bản (BE API + Next.js admin UI) — feature đầu tiên trong pipeline để dựng `apps/catalog` và exercise toàn bộ 6 skills end-to-end. Scope minimal: chỉ Product entity, chưa có Category / Media / Bulk import.

## Problem Statement

**Pain point**: Hệ thống PIM chưa có entity gốc nào. Mọi feature khác (Variant, Channel listing, BOM, POC, ...) đều phụ thuộc vào Product → phải có CRUD Product trước. Đồng thời cần 1 feature đủ nhỏ để test pipeline `ba-spec → db-schema → django-backend → nextjs-frontend → test-generator → code-review` lần đầu.

**Evidence**:
- `CLAUDE.md` status: "Phase 5: First feature — **CRUD Product** (test pipeline)".
- `docs/architecture/full-spec.md` §13 Roadmap MVP Tháng 1–3 item 2: "CRUD `products`, `variants`, `categories`, `media`".
- `docs/architecture/ARCHITECTURE.md`: `apps/catalog` là 1 trong 12 bounded contexts đã được liệt kê.
- User explicit confirm pipeline-test goal: "Foundational entity — chưa có gì cả".

**Persona impacted**: **Catalog Manager** (primary). Super Admin (secondary, dùng Django Admin).

## MVP Alignment

- [x] In current MVP scope (full-spec Roadmap MVP Tháng 1–3 item 2)
- [x] Aligns với primary goal — Product là prerequisite cho mọi flow `idea → poc → variant → sell`.
- [x] Không conflict với "Out of Scope". Bulk import, Category, Media, SEO override defer sang feature riêng.

## Impact

- **Reach**: 100% staff (Catalog Manager dùng trực tiếp; mọi role khác indirect qua Variant/Channel listing FK trỏ Product).
- **Importance**: **Critical** — block toàn bộ MVP, không có Product thì không feature tiếp theo nào chạy được.
- **Confidence**: **High** — yêu cầu explicit trong CLAUDE.md + roadmap, không phải đoán.

## Effort estimate

| Component | Hours |
|---|---|
| DB (Product model + migration + indexes) | 1.0 |
| BE — service layer + selectors + viewset + serializer + permissions | 3.0 |
| BE — Django Admin registration | 0.5 |
| FE — list page (table + filter + pagination) | 2.5 |
| FE — create/edit page (form + zod) | 2.5 |
| FE — delete confirm + toast | 0.5 |
| FE — API hooks (TanStack Query) + types | 1.0 |
| Test — pytest (service + viewset + permissions) | 2.0 |
| Test — Vitest (form schema + hook unit) | 1.0 |
| Test — Playwright (1 happy path e2e) | 1.0 |
| Code review pass | 0.5 |
| **Total** | **~15.5 giờ (~M)** |

## Alternatives considered

- **Django Admin only (skip Next.js page)** — Rejected: bypass FE pipeline test, mất giá trị "exercise 6 skills". Tuy nhiên Django Admin VẪN bật cho super admin (free CRUD), không phải thay thế.
- **Service + viewset only, dev test qua Swagger** — Rejected: mất FE pipeline test; Catalog Manager không có UI dùng.
- **Bao gồm Category + Media ngay** — Rejected: scope phình thành L/XL, kéo dài feature đầu tiên, mất tính "minimal viable" để test pipeline nhanh. Defer feature riêng sau khi pipeline đã chạy ổn.
- **Build Variant trước Product** — Rejected: Variant có FK trỏ Product, logical order là Product trước.

## Risks

- **Risk 1 — Scope creep**: dễ bị kéo thêm Category, Media, SEO trong quá trình build vì "đằng nào cũng phải có". Mitigation: giữ ANALYSIS này làm contract, refuse scope mới → tạo feature mới.
- **Risk 2 — Schema decision lock-in**: Product schema sẽ là FK target cho nhiều bảng. Nếu chọn field sai sẽ phải migrate đau. Mitigation: bám sát schema trong full-spec §1; field nào không chắc → đặt `null=True` hoặc dùng `attributes` JSONB.
- **Risk 3 — `sku_root` collision**: full-spec §2 nói `sku_root` unique + format `[CAT3]-[PROD6]` nhưng feature này chưa có Category → manual nhập `sku_root` 6 ký tự, hậu kiểm với regex (BR-002 chưa bind vì BR-002 áp variant SKU). Mitigation: validate unique + format regex ở serializer.
- **Risk 4 — Permission model chưa có**: User/Role chưa scaffold. Mitigation: dùng `IsAuthenticated` tạm, để feature `accounts/RBAC` sau lock down. Audit log mọi mutation (BR-009).
- **Risk 5 — Soft delete behavior**: Product có nhiều FK reverse (Variant, ChannelListing). Khi xóa Product có Variants → block thay vì cascade. Mitigation: viết rõ trong SPEC, test case explicit.

## Recommendation

🟢 **BUILD NOW**

**Reasoning**: Feature đáp ứng cả 3 tiêu chí: (1) trong MVP scope rõ ràng và là critical-path; (2) effort hợp lý (~15h ≈ 2 ngày dev), không phình to; (3) đúng vai trò "first feature" để test pipeline 6 skills end-to-end. Risks đều có mitigation rõ.

Success criteria explicit theo confirm của user: API < 500ms p95, test coverage ≥ 80%, pipeline 6 skills chạy hết.

## Next steps

→ User confirm 🟢 → vào **PHA 2**: viết SPEC.md (acceptance criteria Given-When-Then + edge cases), DESIGN.md (data flow + file structure + API contract), TASKS.md (breakdown 1-2h chunks).

---

*Created by skill: `ba-spec` | Date: 2026-05-26 | Reviewer: squad1@gosmartlog.com*
