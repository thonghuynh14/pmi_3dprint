# Architecture

## High-level diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          User (browser)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                ┌────────────▼────────────┐
                │   Next.js 14 (Vercel)   │  ← Frontend (SSR + CSR)
                │   /admin   /pos         │
                └────────────┬────────────┘
                             │ REST API (axios + JWT)
                ┌────────────▼────────────┐
                │   Django 5 + DRF        │  ← Backend
                │   - ViewSets (thin)     │
                │   - Services (logic)    │
                │   - Selectors (queries) │
                │   - Celery tasks        │
                └────────────┬────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
┌──────▼──────┐    ┌─────────▼────────┐    ┌──────▼──────┐
│ Postgres 16 │    │ S3-compat Storage│    │   Redis     │
│             │    │                  │    │ (Celery +   │
│ Dev: Docker │    │ Dev: MinIO       │    │   cache)    │
│ Prod: Supa- │    │ Prod: Supabase   │    │             │
│   base      │    │                  │    └─────────────┘
│             │    │  - STL files     │
│ - All data  │    │  - GLB previews  │
│ - JSONB     │    │  - Images        │
│ - ltree     │    └──────────────────┘
│ - pg_trgm   │
└─────────────┘

       │
       ├─── Celery workers ────────────────────┐
       │                                        │
       │  Queues: shopee_sync, lazada_sync,     │
       │  tiki_sync, webhooks, reconcile,       │
       │  file_processing                       │
       │                                        │
       └─── External APIs ──────────────────────┤
                                                │
        ┌──────────────┬─────────────┬──────────┴──┐
        │   Shopee     │   Lazada    │    Tiki     │
        │  Open API    │  Open API   │  Open API   │
        └──────────────┴─────────────┴─────────────┘
```

## Layered architecture (Backend)

```
HTTP Request
    ↓
[Middleware] auth, CORS, request_id
    ↓
[ViewSet] thin, parse + delegate
    ↓
[Permission] role-based check
    ↓
[Serializer Input] validate format
    ↓
[Service Layer] business logic, transactions, audit log
    │
    ├── [Selector] for reads
    ├── [Validators] for business rules (BR-001 → BR-010)
    ├── [Manager/Custom QuerySet] for complex queries
    └── [External Connectors] Shopee/Lazada/Tiki
    ↓
[ORM Model] save, with constraints + signals (minimal)
    ↓
[Database] Postgres with check constraints, indexes
    ↓
[Serializer Output] format response
    ↓
HTTP Response
```

**Async path** (cho marketplace sync, file processing):

```
ViewSet → Service → Celery task (.delay)
                ↓
        Celery Worker picks up
                ↓
        Service.do_actual_work()
                ↓
        Update DB + audit log
                ↓
        Webhook notify FE (optional)
```

## Folder structure

```
3dprint-pim/
├── CLAUDE.md                       # Context for Claude Code
├── README.md
├── .gitignore
├── docker-compose.yml              # Local Redis + (optional) Postgres
├── .env.example                    # Template, không commit .env thật
│
├── docs/                           # Documentation
│   ├── README.md
│   ├── product/
│   ├── architecture/
│   └── features/
│
├── .claude/
│   └── skills/                     # 6 skills (commit cùng repo)
│
├── backend/                        # Django project
│   ├── manage.py
│   ├── pyproject.toml              # Dependencies
│   ├── pytest.ini / pyproject.toml [tool.pytest]
│   ├── .env.example
│   ├── conftest.py                 # Shared pytest fixtures
│   │
│   ├── config/                     # Project settings
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   ├── prod.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── apps/                       # Django apps (1 app = 1 bounded context)
│   │   ├── core/                   # Shared models (TimestampedModel, AuditLog, ...)
│   │   ├── accounts/               # User + RBAC
│   │   ├── catalog/                # Product, Category, Brand
│   │   ├── skus/                   # Variant, SkuCode
│   │   ├── design_files/           # STL/GLB management
│   │   ├── materials/              # Material master
│   │   ├── manufacturing/          # Printer, BOM
│   │   ├── poc/                    # POC versions + costing
│   │   ├── ideas/                  # Idea pipeline
│   │   ├── channels/               # Shopee/Lazada/Tiki connectors
│   │   ├── orders/                 # Unified orders
│   │   └── pos/                    # POS endpoints
│   │
│   └── tests/                      # Cross-app integration tests
│
└── frontend/                       # Next.js project
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.mjs
    ├── components.json             # shadcn config
    ├── playwright.config.ts
    ├── vitest.config.ts
    ├── .env.example
    │
    └── src/
        ├── app/                    # App Router routes
        │   ├── (auth)/             # Login, register
        │   ├── (admin)/            # Admin panel (protected)
        │   │   ├── layout.tsx
        │   │   ├── products/
        │   │   ├── variants/
        │   │   ├── design-files/
        │   │   ├── materials/
        │   │   ├── printers/
        │   │   ├── poc/
        │   │   ├── channels/
        │   │   └── orders/
        │   ├── (pos)/              # POS offline (Cashier role)
        │   │   ├── layout.tsx
        │   │   ├── checkout/
        │   │   └── orders/
        │   ├── layout.tsx
        │   ├── page.tsx            # Landing / login redirect
        │   └── globals.css
        │
        ├── components/
        │   ├── ui/                 # shadcn primitives (auto-generated)
        │   ├── forms/
        │   ├── tables/
        │   ├── product/
        │   ├── variant/
        │   ├── design-file/
        │   ├── viewer-3d/
        │   └── layout/
        │
        ├── lib/
        │   ├── api/                # API client + endpoint functions
        │   ├── hooks/              # React Query hooks
        │   ├── schemas/            # zod schemas
        │   ├── types/              # TS types (from OpenAPI)
        │   ├── utils/
        │   └── constants/
        │
        ├── stores/                 # Zustand stores
        ├── messages/               # i18n (vi + en)
        └── middleware.ts           # Auth + i18n routing
```

## Key architectural decisions

### 1. Why Django (not NestJS, FastAPI)?

- User strength: Python proficient
- Maintainability: 1-2 dev team, Django convention ổn định 15+ năm
- Batteries included: admin, migrations, ORM, auth
- DRF mature, marketplace integration code dễ test

### 2. Why Next.js + Django (split) vs Django templates?

- Need POS offline-first (IndexedDB, Service Worker) → SPA
- 3D preview với `<model-viewer>` web component → client-side
- Future mobile app có thể reuse REST API
- Django Admin vẫn dùng cho super admin operations (free CRUD UI)

### 3. Why Supabase (not self-host Postgres)?

- Free tier đủ cho dev + MVP
- Built-in Storage (S3-compatible) cho STL files
- Backup tự động
- Connection pooler (PgBouncer) included
- Migrate self-host khi scale up đơn giản (chỉ là Postgres)

### 4. Why Pattern A (Supabase = Postgres only)?

Chi tiết xem [tech-stack.md - Auth strategy](tech-stack.md#auth-strategy).

Tóm tắt: B2B internal tool 6-10 users, không cần OAuth/magic link → Django auth đơn giản hơn, skills của mình áp dụng được 100%.

### 5. Why service layer pattern (HackSoft)?

- Test business logic không phụ thuộc HTTP
- ViewSet thin, dễ reuse logic ở management commands / Celery
- Tránh fat model (logic scattered)
- Audit log dễ inject

### 6. Why UUID PK (not auto-increment int)?

- Không leak business info (vd "có 5000 variants")
- Distributed ID generation (sau này scale)
- Stable URL trong frontend

### 7. Why JSONB cho `attributes` (not pure relational)?

- 3D printing có nhiều attribute hiếm (food_safe, uv_resistant, finish) — không đáng làm column riêng
- Variant đã có 5 trục chính làm column rồi
- GIN index cho query containment đủ nhanh
- Promote thành column khi 1 key được filter > 1000 lần/ngày

## Data flow ví dụ: Push variant lên Shopee

```
1. [Frontend] Channel Operator click "Publish to Shopee"
   POST /api/v1/variants/{id}/publish_to_channel/
   Body: { channel: 'shopee' }

2. [ViewSet] permission check (role: channel_operator)

3. [Service] channels.services.channel_publish_variant
   - Validate: variant.status == 'active'
   - Validate: design_file.license_allows_commercial (BR-003)
   - Validate: variant has stock > 0 (or warn)
   - Create/update ChannelListing (status='syncing')
   - Trigger Celery task: push_variant_to_shopee.delay(variant_id, shop_id)
   - Return 202 Accepted

4. [Celery worker] push_variant_to_shopee
   - Get MarketplaceCredential, refresh token if needed
   - ShopeeConnector.create_product(listing)
     - Build payload (item_name, images, dimensions, ...)
     - HMAC-SHA256 sign request
     - POST /api/v2/product/add_item
     - Parse response → external_item_id
   - If tier variation needed:
     - ShopeeConnector._init_tier_variations(...)
   - Update ChannelListing:
     external_product_id = ..., status='synced', last_synced_at=now()
   - audit_log(actor=user, action='channel.published', entity=listing)

5. [Frontend] React Query refetch after 2s
   Shows "Published ✓" + link to Shopee listing
```

## Security architecture

- **Auth**: JWT (access 15min + refresh 7d httpOnly cookie)
- **CORS**: explicit allowed origins, no wildcard
- **CSRF**: not applicable for pure API (JWT bearer); enable for any cookie-based session
- **Encryption at rest**: Supabase encrypted volumes; marketplace credentials AES-encrypted column
- **Encryption in transit**: HTTPS everywhere
- **Webhook signature**: verify HMAC trước khi process (Shopee, Lazada)
- **Rate limiting**: per-IP và per-user, qua django-ratelimit hoặc Cloudflare
- **Audit log**: every state change quan trọng (BR-009)
- **RBAC**: role-based, granular permissions (xem [personas.md](../product/personas.md))

## Deployment topology (future)

```
                      ┌─────────────────┐
                      │   Cloudflare    │  ← CDN + WAF
                      └────────┬────────┘
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
        ┌─────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
        │   Vercel   │  │  Railway /  │  │  Supabase   │
        │ (Next.js)  │  │  Render     │  │  (Postgres  │
        │            │  │  (Django)   │  │  + Storage) │
        └────────────┘  └─────────────┘  └─────────────┘
                               │
                        ┌──────▼──────┐
                        │   Redis     │
                        │ (Upstash    │
                        │  serverless)│
                        └─────────────┘
```

Decision deferred until MVP launch.
