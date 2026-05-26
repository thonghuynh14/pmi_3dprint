# Tech Stack

> Tất cả version đã pin. Không upgrade trừ khi có lý do rõ + test pass.

## Summary table

| Layer | Choice | Version |
|---|---|---|
| Backend framework | Django | 5.0.x |
| API framework | Django REST Framework | 3.15.x |
| Database (dev) | PostgreSQL trong Docker | 16 |
| Database (staging/prod) | PostgreSQL (Supabase managed) | 16 |
| Storage (dev) | MinIO (S3-compatible) trong Docker | latest |
| Storage (staging/prod) | Supabase Storage | - |
| Cache + queue broker | Redis | 7.x |
| Async task | Celery | 5.3.x |
| Driver | psycopg | 3.1.x |
| Auth | django-allauth + dj-rest-auth + simplejwt | latest stable |
| Permissions | django-guardian | 2.4.x |
| API docs | drf-spectacular | latest |
| Linter (BE) | ruff | latest |
| Type checker (BE) | mypy + django-stubs | latest |
| Test (BE) | pytest + pytest-django + factory_boy | latest |
| Frontend framework | Next.js (App Router) | 14.2.x |
| Language | TypeScript | 5.4.x |
| Styling | Tailwind CSS | 3.4.x |
| UI primitives | shadcn/ui (Radix-based) | latest |
| Data fetching | TanStack Query | v5 |
| Forms | react-hook-form + zod | latest |
| Tables | TanStack Table | v8 |
| 3D viewer | `<model-viewer>` (Google) | 3.x |
| i18n | next-intl | latest |
| Client state | Zustand | latest |
| Date utils | date-fns | 3.x |
| Test (FE unit/component) | Vitest + @testing-library/react | latest |
| Test (FE e2e) | Playwright | latest |
| Test (FE mock) | MSW | latest |
| Hosting (FE prod) | Vercel | - |
| Hosting (BE prod) | TBD (Railway / Render / VPS) | - |

## Backend decisions

### Django 5 over FastAPI / NestJS

✅ **Chose Django because**:
- User strength: Python proficient
- Maintainability: 1-2 dev team, Django convention ổn định
- Batteries included: ORM, migrations, admin, auth
- Mature ecosystem for e-commerce/PIM patterns
- Django Admin = free CRUD UI cho super admin

❌ **Rejected alternatives**:
- **FastAPI**: nhanh hơn nhưng tự build ORM/migration/auth → time-to-market chậm hơn
- **NestJS**: TypeScript fullstack hấp dẫn, nhưng user không strong TS BE
- **Flask**: quá ít convention, dễ sai

### Django REST Framework over Django Ninja

✅ **DRF**:
- Standard, nhiều tài liệu
- ViewSet, Serializer, Permission battle-tested
- Skills của Claude trong codebase này được viết theo DRF

❌ **Django Ninja**: Modern hơn, có type hints native, nhưng ít lib hỗ trợ (drf-spectacular, django-filter ecosystem)

### Service layer (HackSoft styleguide)

✅ **Why**:
- Test business logic không phụ thuộc HTTP
- ViewSet thin, dễ reuse logic ở management commands / Celery
- Tránh fat model

❌ **Trade-off**: thêm 1 layer (services/), một số dev quen Django "MVC mỏng" sẽ cần adapt

### Celery over Django-Q / RQ

✅ **Celery**:
- Industry standard
- Mature retry/backoff/scheduling
- Multiple queue routing
- Flower monitoring

❌ **Django-Q**: nhẹ hơn, integrated với Django, nhưng ít feature retry phức tạp

### Postgres over MySQL / MongoDB

✅ **Postgres**:
- JSONB + GIN index → dynamic attributes
- ltree cho category tree
- pg_trgm cho fuzzy search
- Strict type system
- Supabase managed = free tier hợp lý

❌ **MySQL**: thiếu ltree, JSONB type không equivalent
❌ **MongoDB**: relational data (BOM, variants, channel listings) phù hợp RDBMS hơn

## Frontend decisions

### Next.js 14 over Remix / SvelteKit / pure Vite

✅ **Next.js**:
- App Router (Server Components) → tốt cho list/detail page
- Vercel hosting tối ưu
- Ecosystem lớn (shadcn/ui, TanStack Query, ...)
- Middleware cho auth routing
- Image optimization built-in

❌ **Remix**: nhỏ hơn ecosystem, hosting phức tạp hơn
❌ **SvelteKit**: Claude viết React tốt hơn Svelte
❌ **Pure Vite + React**: thiếu SSR cần thiết cho SEO của public page

### App Router over Pages Router

✅ **App Router (Next 13+)**:
- Server Components giảm bundle size
- Layouts compose tốt hơn
- Streaming, parallel routes
- Modern direction của React

❌ **Pages Router**: legacy, không có Server Components

### shadcn/ui over Material UI / Ant Design / Chakra

✅ **shadcn/ui**:
- Không phải dependency — code copy vào project, full control
- Radix UI primitives = accessible by default
- Tailwind-based, easy customize
- Modern aesthetic

❌ **Material UI**: design system Google, khó customize, bundle nặng
❌ **Ant Design**: enterprise look, khó override
❌ **Chakra**: ổn nhưng runtime CSS = slower

### TanStack Query over SWR / Apollo (REST)

✅ **TanStack Query**:
- Mature, feature đầy đủ
- Mutation + optimistic updates
- DevTools tốt

❌ **SWR**: thiếu mutation primitives mạnh
❌ **Apollo**: cho GraphQL, dự án này REST

### react-hook-form + zod over Formik / React Final Form

✅ **react-hook-form**:
- Performance tốt (uncontrolled refs)
- Bundle nhỏ
- zod schema = TypeScript types tự động

❌ **Formik**: re-render nhiều, performance kém với form lớn

### TanStack Table v8 over React Table v7 / DataGrid / AG Grid

✅ **TanStack Table v8**:
- Headless = full control UI
- TypeScript native
- Server-side pagination + sorting + filtering API tốt

❌ **AG Grid**: feature-rich nhưng commercial cho advanced, UI khó match shadcn

## Database decisions

### Hybrid pattern: Local Postgres (dev) + Supabase (staging/prod)

**Default cho dự án này.**

| Env | DB | Storage |
|---|---|---|
| Dev (local) | Postgres 16 trong Docker | MinIO (S3-compatible) trong Docker |
| Staging | Supabase Postgres | Supabase Storage |
| Production | Supabase Postgres | Supabase Storage |

✅ **Why Hybrid**:
- **Dev fast iteration**: localhost <1ms vs Supabase 50-200ms latency
- **Offline OK**: code không cần internet
- **Pytest tốc độ**: hàng trăm tests/giây, isolated per-test
- **Test concurrent**: race condition tests (BR-001 SKU collision) dễ
- **Migration safe**: thử nghiệm migrate/rollback không sợ phá prod
- **Free tier Supabase pause** sau 7 ngày idle không ảnh hưởng dev
- **Production-like khi cần**: switch sang Supabase qua đổi `.env`
- **Managed backup ở prod**: Supabase tự lo backup, replication

❌ **Trade-off**:
- 2 environments cần maintain (local schema + Supabase schema)
- Mitigated: Django migrations là single source of truth, apply cùng files lên cả 2

### Why Supabase (cho staging/prod)?

- Free tier 500MB DB + 1GB storage (đủ cho MVP)
- Managed backups, point-in-time recovery
- PgBouncer connection pooler built-in
- S3-compatible Storage cho STL files
- Easy migration sang self-host khi scale (chỉ là Postgres + S3)
- Region Singapore = low latency cho VN users

❌ **Self-host từ đầu**: overhead DevOps cho 1-2 dev team

### Why Postgres (not MySQL / MongoDB)?

- **JSONB + GIN index**: dynamic attributes (xem ARCHITECTURE)
- **ltree extension**: category tree
- **pg_trgm + unaccent**: VN fuzzy search
- **Strict type system**: catch lỗi sớm
- **Migration tools mature** (Django ORM)

❌ **MySQL**: thiếu ltree, JSONB không equivalent
❌ **MongoDB**: relational data (BOM, variants, channel listings) phù hợp RDBMS hơn

### Pattern A (Postgres only) over Pattern B (Supabase Auth + Django)

#### Decision: **Pattern A**

✅ **Why**:
- B2B internal tool 6-10 users → không cần OAuth/magic link
- Django auth đủ tốt + skills đã viết theo
- Đơn giản hơn (1 source of truth cho user)
- Không phải sync user table

❌ **Trade-off**:
- Không tận dụng Supabase Auth (free Google OAuth)
- RLS policies của Supabase bypass khi Django dùng service_role

#### Future migration to Pattern B (nếu cần)
Khi nào migrate:
- Có customer-facing app (POS cho khách hàng tự đăng nhập)
- Cần magic link / OAuth / passwordless

Khi đó:
1. Add `supabase_user_id` column vào `accounts_users`
2. Frontend dùng Supabase Auth SDK
3. Django middleware verify Supabase JWT
4. Sync user info lúc login lần đầu

## Auth strategy

### Token flow

1. User login → POST `/api/v1/auth/login/` với email + password
2. Django validate, return:
   - `access_token` (15 phút TTL) — short-lived, dùng cho mọi API call
   - `refresh_token` (7 ngày TTL) — long-lived, lưu httpOnly cookie
3. Frontend gắn `Authorization: Bearer {access_token}` mỗi request
4. Khi access expired (401):
   - Axios interceptor tự call `/api/v1/auth/refresh/`
   - Get new access_token, retry original request
5. User logout → POST `/api/v1/auth/logout/` → blacklist refresh token

### Why JWT (not session cookies)?

- Stateless: scale BE đơn giản, không phải sync session store
- Mobile app future: token-based dễ hơn
- POS offline: lưu token, sync khi online

### Why refresh token rotation (not just access only)?

- Access token có thể leak (XSS, log) → rotation giảm window of attack
- Refresh trong httpOnly cookie = an toàn hơn localStorage

## Storage strategy

### Files trong Supabase Storage (not DB)

✅ **Why**:
- DB chỉ nên lưu metadata, không phải binary
- Supabase Storage = S3-compatible, dùng boto3 hoặc native SDK
- CDN tự động
- Versioning support

### Path convention

```
{environment}/{entity_type}/{entity_id}/{filename}

Ví dụ:
prod/design-files/uuid-abc/dragon-v2.stl
prod/design-files/uuid-abc/dragon-v2.glb     # preview
prod/products/uuid-xyz/main.jpg
prod/variants/uuid-123/thumb.webp
```

### Upload flow

```
Frontend:
1. POST /api/v1/design-files/upload-presign/ with filename + content_type
2. BE returns: { upload_url, fields, storage_key }
3. Frontend PUT file directly to upload_url (presigned S3 PUT)
4. Frontend POST /api/v1/design-files/ with storage_key (no file)
5. BE creates DesignFile record
6. Trigger Celery: convert STL → GLB preview
```

Lợi ích: BE không proxy file (giảm bandwidth, memory)

## Versioning

- API: `/api/v1/...` (URL versioning)
- DB: Django migrations linear (no branching)
- Frontend: Next.js auto bundle versioning
- Mobile (future): API support v1 + v2 trong 6 tháng minimum

## Dependencies update policy

- **Patch** (0.0.x): update tự do, monthly
- **Minor** (0.x.0): test staging, monthly
- **Major** (x.0.0): plan dedicated sprint, read changelog
- **Security**: hotfix asap, ưu tiên trên mọi thứ
- **Dependabot/Renovate**: enable cho automated PR

## Cost estimate (monthly)

### MVP phase
- Supabase free: $0
- Vercel hobby: $0
- Domain: $10/year = $0.83/month
- Total: **~$1/month**

### Growth phase
- Supabase Pro: $25
- Vercel Pro: $20
- Backend hosting (Railway): $5-20
- Sentry: $0 (free tier 5k events)
- Total: **$50-65/month**

### Scale phase
- Self-host Postgres: $40 (DO Postgres managed)
- VPS for Django + Celery: $20-40
- S3 / R2 storage: $5
- Total: **$65-85/month**
