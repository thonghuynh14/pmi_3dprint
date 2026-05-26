# 3D Printing PIM - Claude Skills Bundle

Bộ 6 skills cho Claude hỗ trợ phát triển hệ thống quản lý sản phẩm/SKU in 3D đa kênh.

**Stack đích**: Django 5 + DRF + PostgreSQL 16 + Celery + Next.js 14 + TanStack Query/Table + shadcn/ui.

## Danh sách skills

| Skill | Trigger | Mô tả |
|---|---|---|
| `ba-spec` | "user story", "spec", "acceptance criteria", "yêu cầu nghiệp vụ" | Viết user story, AC Given-When-Then, edge case checklist, business rules |
| `db-schema` | "schema", "model", "migration", "ERD", "table" | Thiết kế PostgreSQL schema + Django models, migration zero-downtime |
| `django-backend` | "Django", "DRF", "API endpoint", "viewset", "service" | Sinh code BE: models, serializers, services, viewsets, Celery tasks, marketplace connectors |
| `nextjs-frontend` | "frontend", "Next.js", "component", "page", "form", "UI" | Sinh code FE: Server/Client Components, React Query hooks, forms, 3D viewer, POS offline |
| `code-review` | "review", "check code", "audit", "kiểm tra code" | Review code BE/FE theo checklist Critical/Major/Minor với security + performance focus |
| `test-generator` | "test", "pytest", "factory", "Playwright", "viết test" | Sinh test BE (pytest + factory_boy) + FE (Vitest + Playwright) |

## Cài đặt

### Claude.ai (Web/App)

1. Vào **Settings → Capabilities → Skills**
2. Bấm **Upload skill**
3. Upload từng folder (vd `ba-spec/`) hoặc zip toàn bộ
4. Skills sẽ trigger tự động khi user phrase match description

### Claude Code (CLI / Terminal)

```bash
# Copy vào folder skills của Claude Code
mkdir -p ~/.claude/skills
cp -r ba-spec db-schema django-backend nextjs-frontend code-review test-generator ~/.claude/skills/

# Hoặc symlink để dễ update sau
ln -s /path/to/repo/skills/* ~/.claude/skills/
```

Mở Claude Code và kiểm tra: skills sẽ hiển thị trong `/skills` command.

### Project-level (Claude Code)

Nếu muốn skill chỉ active cho project này:

```bash
cd /path/to/your/project
mkdir -p .claude/skills
cp -r /path/to/skills-bundle/* .claude/skills/
```

## Cách hoạt động

Khi user prompt match description của skill (vd "viết user story cho module POC"), Claude tự động load SKILL.md tương ứng và follow guidelines trong đó.

Nếu task phức tạp hơn, Claude load thêm các file trong `references/` (vd `references/templates.md`, `references/sku_generator.md`).

## Workflow thường dùng

### 1. Phát triển feature mới end-to-end

```
1. ba-spec       → Viết user story + AC + edge cases cho feature
2. db-schema     → Thiết kế model + migration
3. django-backend → Sinh service, viewset, serializer
4. nextjs-frontend → Sinh page, form, hooks
5. test-generator → Sinh test cho BE + FE
6. code-review   → Review trước khi merge
```

### 2. Chỉ refine spec

```
ba-spec → "viết acceptance criteria cho US-XXX với edge cases về Tiki 2-axes"
```

### 3. Review PR

```
code-review → paste code → checklist + severity ratings
```

## Customization

Mỗi skill có thể edit:

- **SKILL.md**: thêm/sửa convention, anti-patterns, examples
- **references/*.md**: thêm pattern mới, business rules, template

Khi thay đổi, không cần reload — Claude đọc lại khi skill trigger lần sau.

## Lưu ý

- 6 skills này thiết kế cho dự án 3D Printing PIM cụ thể. Có domain knowledge: marketplace constraints (Tiki 2-axes), license CC, BOM theo filament gram, SKU pattern `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`.
- Stack cố định: Django + Next.js. Đổi stack → cần edit `django-backend/SKILL.md` và `nextjs-frontend/SKILL.md`.
- Business rules BR-001 → BR-010 reference trong nhiều skills — sync nếu thay đổi.

## Quick reference

### Business rules đã encode trong skills

- **BR-001**: SKU unique toàn hệ thống (case-insensitive)
- **BR-002**: SKU pattern `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`, 12-24 chars
- **BR-003**: Variant không active được nếu `license_allows_commercial = false`
- **BR-004**: Tiki block khi > 2 option attributes
- **BR-005**: POC cost = material + electricity + depreciation + labor + failure_buffer
- **BR-006**: Stock sync giữa các kênh < 30s
- **BR-007**: Safety stock buffer 5-10% mỗi kênh
- **BR-008**: STL > 100MB phải có GLB preview
- **BR-009**: Audit log mọi state change quan trọng
- **BR-010**: Internal barcode EAN-13 prefix 020-029

### 6 Roles

- Super Admin / Catalog Manager / Production Manager / Channel Operator / Designer / Cashier

### Marketplace specifics

- **Shopee**: HMAC-SHA256 sign, token TTL 4h, 50 variants/stock call
- **Lazada**: OAuth + signed XML, token TTL 7d, SPU/Product/SKU hierarchy
- **Tiki**: OAuth 2.0, **MAX 2 option attributes**

---

Generated 2026-05-26 by Claude Skill Creator session.
