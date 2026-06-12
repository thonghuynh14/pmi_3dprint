# ADR 0001: Custom User Model + Cookie-based JWT

**Date**: 2026-06-12
**Status**: Accepted
**Feature**: 03-accounts-rbac

## Context

Sau khi feature 01 (Product) + 02 (Variant) ship, hệ thống có 4 deferred items tích lại liên quan auth/permission:
- Token storage XSS risk (access token ở localStorage)
- Refresh flow chưa hoạt
- Không có middleware route guard
- ViewSet chỉ `IsAuthenticated`, không phân biệt role

Hệ thống dự kiến phục vụ 6 role (super_admin / catalog_manager / production_manager / channel_operator / designer / cashier) với permission matrix khác biệt rõ — không gỡ blocker này thì không thể mở multi-user.

## Decisions

### 1. Custom User Model (swap `AUTH_USER_MODEL`)

Tạo `accounts.User` extends `AbstractBaseUser + PermissionsMixin` thay vì dùng default `auth.User`.

**Rationale**:
- Cần thêm field `role` (FK Role) và `full_name` (1 chuỗi, tiếng Việt) — `auth.User` có `first_name + last_name` không phù hợp.
- Cần custom `UserManager` cho seed test users qua management command.
- Django docs khuyến nghị custom user model **TỪ ĐẦU** project; swap giữa chừng "significant undertaking".

**Alternatives rejected**:
- *AbstractUser*: kéo theo `first_name/last_name` không cần thiết.
- *Profile model OneToOne*: phải JOIN mọi query lấy role; complexity cao hơn.
- *guardian object-level permissions*: scope quá lớn cho team 6-10, defer khi cần multi-tenant.

### 2. Reset dev DB (không data migrate)

Phân tích ban đầu chốt "data migration" giữ `auth_user` data; sau khi prototype phát hiện gotcha:
- Migration history record `auth.0012_...` dependency. Sau swap, Django detect inconsistency.
- Phải hack `django_migrations` table hoặc `--fake` selectively → fragile (break khi clone repo / setup mới).

**Decision**: drop dev DB + management command `seed_initial_data` tái tạo (6 role + 24 perm + 7 user + 3 product + 18 variant). Effort ~30 phút vs ~5h data migration với risk fragile.

**Production safety**: Production chưa có data nên không ảnh hưởng. ADR này TUYỆT ĐỐI không nên apply trên DB có data thật — phải data migrate hoặc downtime cut-over.

### 3. JWT trong httpOnly cookies (không Bearer header)

Cả `access_token` (TTL 15m) và `refresh_token` (TTL 7d) lưu trong httpOnly Secure SameSite=Lax cookies do BE set qua `/auth/login/`. CSRF protection qua cookie `csrftoken` (non-httpOnly) + header `X-CSRFToken` (axios xsrf built-in).

**Rationale**:
- XSS không steal được token (HTTP-only).
- FE không cần Zustand store cho auth state — browser tự gửi cookie.
- Same-origin via Next.js proxy (`/api/*` → Django) → không cần CORS preflight.

**Trade-off accepted**: cần CSRF token cho mutation. Lợi ích: protection thực sự (vs Authorization header tự miễn nhiễm CSRF).

### 4. Permission claims trong JWT (O(1) check)

Login encode `role` + `permissions: [...]` vào JWT claims (CustomRefreshToken). Permission class đọc từ `request._jwt_claims['permissions']` thay vì DB lookup → O(1).

**Trade-off accepted**: đổi role không invalidate ngay; phải đợi access expire (max 15 phút). Ghi vào BR-012.

**Rationale**:
- Internal tool team 6-10, role hiếm khi đổi.
- DB lookup mỗi request → N+1 latency với 50 req/page.
- Refresh rotation 15m đủ nhanh cho impact.

### 5. `is_superuser` short-circuit ở permission class

`HasPermission` + `ActionPermission` bypass mọi check nếu `user.is_superuser=True` (chuẩn Django `PermissionsMixin.has_perm()`).

**Rationale**:
- Test fixtures dùng `UserFactory(is_superuser=True)` không cần seed 24 perm + 6 role mỗi test → tests cũ pass sau swap không cần refactor.
- Django shell `createsuperuser` cho phép admin bypass debug RBAC khi cần.

## Consequences

### Positive
- Auth state stateless ở FE (browser handle cookie).
- Permission check O(1) qua JWT claims.
- Test cũ pass không cần refactor (is_superuser short-circuit).
- BE permission matrix testable parametrize: 6 role × N action × 3 viewset.

### Negative
- Reset dev DB là one-way migration; mọi dev cùng team phải pull + re-seed.
- JWT claim stale tối đa 15m khi đổi role (mitigate: force re-login nếu cần ngay).
- Cookie strategy yêu cầu CSRF token cho mutation — thêm 1 endpoint round-trip lúc bootstrap.

### Reverted/Migrated
- `lib/api/client.ts`: gỡ `setAccessToken/getAccessToken/bootstrapAccessTokenFromStorage` (localStorage flow cũ).
- Login page: gỡ token storage logic; chỉ dùng `useLogin` mutation.
- Admin layout: gỡ `bootstrapAccessTokenFromStorage` từ `Providers` + replace bằng `useAuth`.

## References
- [SPEC](../../features/03-accounts-rbac/SPEC.md)
- [DESIGN](../../features/03-accounts-rbac/DESIGN.md)
- [Django docs — Changing AUTH_USER_MODEL](https://docs.djangoproject.com/en/5.1/topics/auth/customizing/#changing-to-a-custom-user-model-mid-project)
- [OWASP Cheatsheet — JWT in cookie](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html#token-storage-on-client-side)
