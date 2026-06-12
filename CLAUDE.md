# Claude Code Instructions cho 3D Printing PIM

## Về dự án

Hệ thống quản lý sản phẩm và SKU cho doanh nghiệp in 3D, bán đa kênh (Shopee + Lazada + Tiki + POS offline). Internal tool cho team 6-10 người (Catalog Manager, Production Manager, Channel Operator, Designer, Cashier, Super Admin).

**Spec đầy đủ**: [docs/architecture/full-spec.md](docs/architecture/full-spec.md) ← Single source of truth, khi conflict tin file này.

**PRD ngắn gọn**: [docs/product/PRD.md](docs/product/PRD.md)

## Về người làm việc cùng bạn

- **Mức độ kỹ thuật**: có kinh nghiệm Python, sử dụng VS Code, biết Git cơ bản
- **Ngôn ngữ ưu tiên**: Tiếng Việt (chat) + English (code, comments khi cần kỹ thuật)
- **Style giao tiếp**: chi tiết khi giới thiệu concept mới, ngắn gọn khi đã quen
- **Cách hỏi**: 1 câu/turn, không bombard nhiều câu cùng lúc

## Tech Stack

- **Backend**: Django 5 + Django REST Framework 3.15 + PostgreSQL 16 + Celery + Redis
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query/Table
- **Database**: Hybrid pattern
  - **Dev**: Local Postgres 16 + MinIO trong Docker (fast, offline, isolated)
  - **Staging/Prod**: Supabase Postgres + Supabase Storage (managed)
- **Auth**: Django (KHÔNG dùng Supabase Auth — Pattern A)
- **Hosting dev**: local Docker compose
- **Hosting prod**: TBD (Railway / Render / VPS — quyết sau khi MVP xong)

Chi tiết: [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md)

## Cấu trúc thư mục

```
3dprint-pim/
├── CLAUDE.md                      ← File này
├── README.md
├── .gitignore
├── docs/                          ← Tài liệu sống
│   ├── README.md                  Index docs
│   ├── product/
│   │   ├── PRD.md                 Product Requirements
│   │   └── personas.md            6 roles + persona profiles
│   ├── architecture/
│   │   ├── ARCHITECTURE.md        High-level architecture
│   │   ├── tech-stack.md          Stack decisions
│   │   ├── conventions.md         Coding conventions
│   │   ├── business-rules.md      BR-001 → BR-010
│   │   ├── full-spec.md           ★ SPEC GỐC ★
│   │   └── glossary.md            3D printing + e-commerce terms
│   └── features/
│       ├── _template/             Template cho feature mới
│       │   ├── ANALYSIS.md
│       │   ├── SPEC.md
│       │   ├── DESIGN.md
│       │   └── TASKS.md
│       ├── 01-product-crud/
│       └── ...
├── .claude/
│   └── skills/                    ← 6 skills (commit cùng repo)
│       ├── ba-spec/
│       ├── db-schema/
│       ├── django-backend/
│       ├── nextjs-frontend/
│       ├── code-review/
│       └── test-generator/
├── backend/                       ← Django project (scaffold sau)
│   ├── manage.py
│   ├── pyproject.toml
│   ├── config/
│   └── apps/
└── frontend/                      ← Next.js project (scaffold sau)
    ├── package.json
    └── src/
```

Chi tiết: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

## ⚡ Quy trình thêm feature mới (BẮT BUỘC - KHÔNG BYPASS)

```
User request feature
   ↓
[ba-spec PHA 1] Hỏi 6 câu → ANALYSIS.md → verdict 🟢🟡🟠🔴
   ↓ STOP, đợi user confirm
   ↓
(nếu 🟢 BUILD NOW)
[ba-spec PHA 2] Hỏi 3-5 câu detail → SPEC.md + DESIGN.md + TASKS.md
   ↓ STOP, đợi user review
   ↓
[db-schema] (nếu cần đổi schema) → models + migration
[django-backend] → services, viewsets, serializers theo TASKS
[nextjs-frontend] → pages, components, hooks theo TASKS
[test-generator] → tests cho mỗi service/component
   ↓
[code-review] → checklist trước commit
   ↓
git commit (Conventional Commits)
```

**KHÔNG bypass step nào**, kể cả feature nhỏ. Gate tồn tại để tránh feature creep.

## Available Skills

| Skill | Trigger | Output |
|-------|---------|--------|
| `ba-spec` | "tôi muốn thêm", "let's build", new feature idea, "viết user story", "spec cho ..." | ANALYSIS.md (PHA 1) → SPEC/DESIGN/TASKS.md (PHA 2) |
| `db-schema` | "schema", "model", "migration", "ERD" | Django models + migrations |
| `django-backend` | "Django", "API endpoint", "viewset", "service", "code BE" | Models, serializers, services, viewsets, Celery tasks |
| `nextjs-frontend` | "frontend", "page", "component", "FE", "UI", "form" | Pages, components, hooks, forms |
| `code-review` | "review", "check code", "audit", trước commit | Findings báo cáo theo severity 🔴🟠🟡 |
| `test-generator` | "test", "pytest", "Playwright", "Vitest" | Test files với factory_boy / Vitest / Playwright |

## Coding Conventions

### Commit messages — Conventional Commits

```
feat(catalog): add product CRUD endpoints
fix(skus): SKU generator handles sequence gap
docs(architecture): update tech stack rationale
test(skus): add license blocking test cases
refactor(channels): extract shopee signature helper
chore(deps): bump django 5.0.0 → 5.0.4
```

Scope optional nhưng khuyến nghị (`catalog`, `skus`, `channels`, `auth`, etc.)

### Comments — sparse, tiếng Việt OK

- Comment "tại sao" không comment "cái gì"
- Function name + docstring đủ rõ → không cần comment thêm
- Tiếng Việt OK cho business logic phức tạp (vd: `# Tiki chỉ cho phép tối đa 2 option attributes`)
- Code identifier (variable, function, class) → English

### File size

- File code > 200 dòng → cân nhắc tách
- SKILL.md / docs có thể dài hơn

### Indent

- Python: 4 spaces (PEP 8)
- TypeScript/TS/JSON: 2 spaces

### Naming

- Python: `snake_case` cho variable/function, `PascalCase` cho class
- TypeScript: `camelCase` cho variable/function, `PascalCase` cho component/type
- Files Python: `snake_case.py`
- Files React: `kebab-case.tsx` cho file, component name `PascalCase`
- Django app: `snake_case`, plural (`apps/skus`, `apps/design_files`)
- DB table: `{app}_{plural}` (`catalog_products`, `skus_variants`)

Chi tiết: [docs/architecture/conventions.md](docs/architecture/conventions.md)

## Lệnh thường dùng

### Backend

```bash
cd backend
source .venv/bin/activate

python manage.py runserver       # Dev server :8000
python manage.py makemigrations  # Tạo migration
python manage.py migrate         # Apply migration
python manage.py createsuperuser
python manage.py shell           # Django shell

pytest                           # Run tests
pytest -x                        # Stop on first fail
pytest apps/skus                 # Test 1 app
pytest -k test_variant_create    # Test theo name pattern
pytest --cov=apps                # Coverage

celery -A config worker -l info        # Celery worker
celery -A config beat -l info          # Celery beat scheduler

ruff check .                     # Lint
ruff format .                    # Format
mypy apps/                       # Type check
```

### Frontend

```bash
cd frontend

npm run dev                      # Dev server :3000
npm run build                    # Build production
npm run lint                     # ESLint
npm run typecheck                # tsc --noEmit
npm test                         # Vitest
npm run test:e2e                 # Playwright
npx shadcn-ui@latest add button  # Add shadcn component
```

### Docker (dev)

```bash
docker compose up -d             # Start postgres + redis
docker compose down              # Stop
docker compose logs -f redis     # Tail logs
```

## ⛔ KHÔNG làm

- ❌ KHÔNG tự cài npm/pip package → luôn hỏi user trước, giải thích lý do
- ❌ KHÔNG commit file `.env*`, `credentials.txt`, `*.pem`, `*.key` → xem `.gitignore`
- ❌ KHÔNG bypass pipeline BA → SPEC → CODE → REVIEW
- ❌ KHÔNG sửa file trong `frontend/src/components/ui/` (shadcn auto-generated, dùng `npx shadcn-ui add` để re-generate)
- ❌ KHÔNG dùng `any` trong TypeScript → dùng `unknown` + narrow, hoặc define type
- ❌ KHÔNG để file code > 200 dòng → tách module/component
- ❌ KHÔNG dùng Supabase Auth (auth dùng Django, xem tech-stack.md)
- ❌ KHÔNG put business logic trong serializer/view → delegate sang `services/`
- ❌ KHÔNG raw SQL với f-string user input → dùng parameterized hoặc ORM
- ❌ KHÔNG hard-code marketplace credentials → qua `MarketplaceCredential` model encrypted

## 🚨 Khi gặp lỗi

1. **Đọc kỹ error message** trước khi đoán
2. **Tự fix** nếu rõ ràng:
   - Typo, syntax error
   - Missing import
   - Wrong type
3. **Hỏi user** nếu liên quan:
   - Logic / architecture decision
   - Schema change ảnh hưởng nhiều bảng
   - Migration không reversible
   - External API change (Shopee/Lazada/Tiki)
4. **Giải thích nguyên nhân** bằng tiếng Việt sau khi fix
5. **Loop fix > 3 lần** → STOP, `git reset --hard` về commit trước, mô tả lại từ đầu

## 📞 Khi cần clarify

- Hỏi **1 câu/lần**, đợi user trả lời
- KHÔNG bombard 5 câu cùng lúc
- Đề xuất 2-3 options khi có thể, để user chọn nhanh hơn

## 🔑 Business rules quan trọng (encode trong skills)

- **BR-001**: SKU unique toàn hệ thống (case-insensitive)
- **BR-002**: SKU pattern `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`, length 12-24
- **BR-003**: Variant không active được nếu `design_file.license_allows_commercial = false`
- **BR-004**: Tiki block khi > 2 option attributes (suggest merge axes)
- **BR-005**: POC cost = material + electricity + depreciation + labor + failure_buffer
- **BR-006**: Stock sync giữa các kênh < 30s từ master change
- **BR-007**: Safety stock buffer 5-10% mỗi kênh chống overselling
- **BR-008**: STL > 100MB phải có GLB preview generated trước khi variant active
- **BR-009**: Audit log mọi state change quan trọng (license, price, stock, variant status)
- **BR-010**: Internal barcode EAN-13 prefix 020-029 (GS1 prefix 893 chỉ khi đã đăng ký)
- **BR-011**: JWT access TTL 15m / refresh TTL 7d, rotation BẬT + blacklist BẬT
- **BR-012**: Permission claims trong JWT — invalidate khi access expire (≤ 15m delay)
- **BR-013**: User `is_active=False` → reject ngay (kể cả token còn hạn)
- **BR-014**: Logout blacklist refresh + delete cookies (idempotent)

Chi tiết: [docs/architecture/business-rules.md](docs/architecture/business-rules.md)

## 🏁 Status hiện tại

- [x] Phase 0: Discovery + spec gốc done
- [x] Skills system setup (6 skills)
- [x] Docs structure
- [x] CLAUDE.md
- [x] Phase 1: Foundation (scaffold Django + Next.js) — commit `ca23db4`
- [x] Phase 5: Feature 01 — **CRUD Product** (test pipeline) — commits `91ddf64` (BE) + `c14c9f1` (FE)
- [x] Phase 5: Feature 02 — **CRUD Variant + matrix bulk** — commits `9414a2b` (BE) + `18e476b` (FE)
- [x] Phase 5: Feature 03 — **Accounts / RBAC + JWT cookie auth** — commit BE `905897f`

**Đã chốt trong quá trình build** (deviation so với spec ban đầu):
- **Django 5.1.x** (thay 5.0.x) — hỗ trợ Python 3.13 ở máy dev
- **Tailwind 3.4 + shadcn classic "new-york"** (không dùng base-nova/Tailwind v4)
- Deps FE thêm: `tailwindcss-animate`, `@radix-ui/react-slot` (deps mặc định shadcn classic)
- Test stack FE: Vitest + Testing Library + MSW + Playwright
- **Variant axes v1** = 3 trục (material/color/size), defer 5-trục (layer_resolution + infill) sang feature sau khi có nhu cầu thực tế.

**Đã GỠ ở feature 03 (accounts/RBAC)**:
- ✅ Auth UI cookie-based (httpOnly access + refresh, XSS-resistant)
- ✅ Middleware route guard `/admin/*` + `/pos/*`
- ✅ RBAC permission ở viewset: ActionPermission + JWT claims O(1)
- ✅ 6 role + 24 permission + 7 test user seed qua management command

**Deferred (defer thêm)**:
- i18n wiring (next-intl đã cài, strings còn hardcode) — defer riêng feature i18n
- E2E Playwright cho variant matrix flow chưa chạy (file viết xong, cần Docker daemon up)
- `AuditLog.changes` Decimal serialize: hiện workaround `_jsonify(data)` cục bộ — chuyển encoder vào core/models AuditLog
- AlertDialog thay `window.confirm()` cho warn > 50 variants ở matrix UI
- 5-trục variants (layer_resolution_mm + infill_percent) khi user thực sự cần
- UI quản lý user CRUD web (super_admin dùng Django Admin) — defer cho đến khi team > 10 người
- Object-level permission (django-guardian) — defer khi cần multi-tenant
- 2FA / OTP / SSO / password reset email — out of MVP scope

**Next action**: Ứng viên feature 04 theo roadmap MVP:
- `design-files` — upload STL/GLB + license tracking (BR-003 sẵn sàng wire vào variant, Designer role đã có)
- `materials/BOM` — master data nguyên vật liệu + công thức (BR-005 POC cost prep)
- `pos-app` — POS UI cho cashier (đã có role + permission `order:create_pos`)

Prompt: "Tôi muốn thêm tính năng [X]" → kick off `ba-spec` PHA 1.
