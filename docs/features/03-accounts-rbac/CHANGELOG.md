# Changelog: Accounts / RBAC (feature 03)

## 2026-06-12 — Phase 2: Frontend (cookie auth + RBAC guard)

### Added
- **Auth API + types**: `lib/api/auth.ts` (login/logout/refresh/getMe) + `lib/types/auth.ts` (AuthUser/MeResponse/RoleCode).
- **Axios refactor**: `withCredentials: true` + `xsrfCookieName/xsrfHeaderName` cho CSRF + 401 → /auth/refresh/ → retry interceptor (lock concurrent refresh). Gỡ localStorage token flow cũ.
- **`useAuth` hook**: fetch /me/ + cache infinite, invalidate sau login/logout. `useLogin/useLogout/usePermission/useAnyPermission/useAllPermissions` helpers.
- **Permission helpers**: `lib/auth/permissions.ts` — `hasPermission/hasAny/hasAll` (UX guard, BE luôn enforce).
- **Middleware route guard**: `src/middleware.ts` — protect `/admin/*` + `/pos/*` (check `access_token` cookie). Reverse-guard /login → /admin nếu đã login.
- **Login page refactor**: dùng `useLogin` mutation, redirect theo `next` query param (same-origin), toast Vietnamese error.
- **Admin layout**: hiển thị `username + role badge`, logout button gọi `useLogout` + invalidate cache + redirect /login.
- **`<PermissionGuard>` component**: wrap nút "Tạo product"/"Thêm matrix"/"Thêm variant"/"Xoá"/"Khôi phục" với perm code tương ứng.
- **MSW handlers cho auth**: login (smoke/catmgr/cashier mapping) + me + refresh + logout (test isolation).
- **Tests**: 18 FE test mới (12 permission helpers + 6 useAuth/login/logout/permission hooks).

### Verified
- 84/84 FE Vitest pass (66 cũ + 18 mới). `tsc --noEmit` clean.

### Deferred
- E2E Playwright cho login flow (smoke + cashier guard) — file chưa viết, cần Docker daemon.
- i18n wire (next-intl) — out of feature scope.
- POS-specific layout cho cashier (auto-redirect /pos).

### Commit
- `<pending>` `feat(accounts): cookie-based auth + RBAC guard FE`

---

## 2026-06-12 — Phase 1: Backend (custom User + RBAC + JWT cookie)

### Added
- **`apps/accounts`**: custom `User` (BigAutoField PK + FK Role) extends `AbstractBaseUser + PermissionsMixin`. Custom `UserManager`. `Role` + `Permission` model (M2M).
- **Constants**: 24 permission code (format `domain:action`) + 6 role definition + ROLE_PERMISSIONS mapping (mirror personas.md matrix).
- **Migration**: `0001_initial` create 3 table + AUTH_USER_MODEL=accounts.User. **Reset dev DB** thay vì data migration (xem ADR-0001).
- **`seed_initial_data` command**: idempotent seed 24 perm + 6 role + 7 user (smoke super + 5 test 1-per-role) + 3 sample product + 18 variant.
- **JWT claims**: `CustomRefreshToken` inject role + permissions[] vào access + refresh token. Permission check O(1) đọc từ `request._jwt_claims`.
- **`CookieJWTAuthentication`**: đọc `access_token` từ httpOnly cookie thay vì `Authorization` header. Check `is_active` reject deactivated user.
- **Permission classes**: `HasPermission(code)` + `ActionPermission` (map view.action → perm code). `is_superuser` short-circuit (chuẩn Django).
- **4 auth endpoint**: POST /login/ (set 2 cookies + csrftoken) · POST /refresh/ (rotation BẬT) · POST /logout/ (blacklist + clear cookies) · GET /me/ (user + permissions).
- **Wire vào ViewSet**: ProductViewSet + VariantViewSet + ProductVariantMatrixView dùng ActionPermission map.
- **Tests**: 83 accounts test (model/JWT/auth/permission/services/API/matrix). Permission matrix parametrize 6 role × 3 viewset = 18 cases.

### Verified
- 290/290 BE pytest pass (4.7s). Coverage accounts: 96.7% (trừ seed CLI 87 stmt, smoke-tested live).
- Smoke cURL pass: login smoke → 201 product, login cashier → 403 product create.

### Decisions chốt
- **Reset DB > data migration** do Django docs warn `AUTH_USER_MODEL` swap với history.
- **JWT in cookie > Bearer header** (XSS-resistant, simpler FE state).
- **Permission in JWT claims > DB lookup** (O(1), trade-off 15m stale).
- **is_superuser short-circuit** → tests cũ pass không refactor.

### Commit
- `905897f feat(accounts): add custom User + RBAC + JWT cookie auth`

### Migration safety
- `backup_pre_accounts.sql` (97KB) snapshot DB cũ — gitignored, local only.
- Production chưa có data → reset không impact.
