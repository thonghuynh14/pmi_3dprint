# 3D Printing PIM - Product Requirements Document

> Version: 0.1 | Date: 2026-05-26 | Status: Draft

> ⚠️ Tài liệu này là **bản tóm tắt cao cấp**. Chi tiết kỹ thuật xem [full-spec.md](../architecture/full-spec.md).

## 1. Overview

- **Name**: 3D Printing PIM (Product Information Management)
- **One-liner**: Hệ thống quản lý sản phẩm + SKU + đa kênh dành riêng cho doanh nghiệp in 3D bán Shopee/Lazada/Tiki + POS offline.
- **Domain**: B2B internal tool, e-commerce, manufacturing

## 2. Problem Statement

Doanh nghiệp in 3D bán đa kênh hiện gặp:

1. **Variant explosion**: 1 sản phẩm có 30-100 SKU (material × color × size × layer res × infill) — quản lý bằng Excel + copy paste lên các sàn → nhầm lẫn, mất thời gian
2. **Overselling**: stock không sync giữa các kênh → cancel order → tụt rating
3. **Cost không chính xác**: không track filament/electricity/depreciation → bán lỗ mà không biết
4. **File STL/license rối**: nhiều version, không biết file nào license CC BY-NC (không được bán)
5. **POS rời rạc**: bán offline phải tính tay, không sync stock với online

## 3. Target Persona

6 roles staff trong doanh nghiệp 5-20 người. Chi tiết: [personas.md](personas.md).

**Personas chính**:
- **Catalog Manager** (anh Hùng, 28t) — tạo + quản lý SP, biggest user
- **Production Manager** (chị Lan, 35t) — track material, máy in, BOM
- **Channel Operator** (em Minh, 24t) — sync đa kênh, monitor stock
- **Designer** (anh Tuấn, 30t) — upload file thiết kế, manage version
- **Cashier** (chị Hoa, 40t) — POS offline
- **Super Admin** — toàn quyền

## 4. MVP Scope

### 4.1. Must have (Phase 1, 3 tháng)

- ✅ Catalog: CRUD Product/Category/Brand
- ✅ SKU/Variant: generate SKU theo pattern, variant matrix UI
- ✅ Design Files: upload STL, version, license CC
- ✅ Materials + BOM: define vật liệu, BOM theo gram
- ✅ Printers database: máy in + compatibility
- ✅ POC/Costing: nhập kết quả in → cost breakdown
- ✅ Auth + RBAC: 6 roles
- ✅ **Shopee sync**: push variant, sync stock 2 chiều (kênh đầu tiên)
- ✅ Audit log

### 4.2. Phase 2 (3 tháng tiếp)

- Lazada sync
- Tiki sync (với 2-axes constraint)
- 3D preview (model-viewer)
- Ideas pipeline (Kanban)
- POS offline-first

### 4.3. Out of scope (Phase 3+)

- Multi-tenant
- AI image generation
- Mobile native app
- Customer-facing storefront
- Inventory forecasting AI

## 5. User Flows (3 quan trọng nhất)

### Flow 1: Tạo sản phẩm mới với 6 variants

```
Catalog Manager: Login → Create Product → Upload STL → Set CC0 license
  → Add 3 colors + 2 sizes → "Generate variants" → preview 6 SKU
  → Edit cost price per variant → Save (status: draft)
  → Channel Operator: Push lên Shopee → Sandbox test → Production push
  → Live trên Shopee
```

### Flow 2: Production logs POC, tính cost

```
Production Manager: Login → Open variant → "Add POC version"
  → Nhập: printer used, time (4h30), filament used (45g), notes
  → System tính: material cost (45g × 400) + electricity (4.5h × 150W × 3000) 
                + depreciation (4.5h × purchase_price/lifetime_hours)
                + labor (5min × 50K/h) + failure_buffer (10%)
  → Suggested price = cost × 2.5 → Catalog Manager review → Apply price
```

### Flow 3: Stock sync khi POS bán

```
Cashier (POS offline): Scan barcode → SKU "FIG-DRAGON-PLA-RED-M-01"
  → Quantity 1, cash payment → Print receipt
  → (online) Sync order về server
  → Server: decrement master stock from 5 → 4
  → Fan-out to Shopee/Lazada/Tiki: update stock 4
  → Within 30s, all channels show stock = 4
```

## 6. Tech Stack

Xem [../architecture/tech-stack.md](../architecture/tech-stack.md).

Summary:
- Backend: Django 5 + DRF + PostgreSQL (Supabase) + Celery + Redis
- Frontend: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- Auth: Django (không dùng Supabase Auth)

## 7. Success Metrics (Phase 1)

| Metric | Target | Đo bằng |
|---|---|---|
| Thời gian từ idea → variant live trên Shopee | < 30 phút | Audit log: created_at idea → first ChannelListing.synced_at |
| Overselling rate | < 0.5% orders | Cancel orders / total × 100% |
| SKU naming consistency | 100% | Validation BR-002 phải pass |
| POC cost accuracy | ±10% so với invoice thực | So sánh cost calculated vs purchase order |
| User adoption (active staff) | 100% staff dùng hàng tuần | Login activity |

## 8. Roadmap

| Tháng | Milestones |
|---|---|
| **M1** (Tháng 1) | Foundation: scaffold, auth, RBAC, basic CRUD Product/Variant |
| **M2** (Tháng 2) | Design files + license, Materials + BOM, Printers, POC |
| **M3** (Tháng 3) | Shopee sync, stock fan-out, audit log, basic UI polish, **MVP launch** |
| **M4-M5** | Lazada + Tiki sync, 3D preview, Ideas pipeline |
| **M6** | POS offline, mobile responsive |

## 9. Constraints & Assumptions

- **Team size**: 1-2 developer (vibe coding với Claude Code)
- **Budget**: bootstrapped, ưu tiên free tier (Supabase free, Vercel free)
- **Language**: UI tiếng Việt, code/docs technical mix
- **Users**: 5-20 staff, không phải public
- **Migration**: nếu có data Excel cũ → import script

## 10. Open questions

- [ ] Có cần multi-warehouse không (1 warehouse hay nhiều địa điểm)?
- [ ] Stripe / momo / VNPay cho POS?
- [ ] Tax / VAT calculation cần phức tạp đến đâu?
- [ ] Report/analytics ngoài operational metrics?
