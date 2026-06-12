# Tasks: Accounts / RBAC

Effort total ~28h, chia 3 phase + finalize. Mỗi task có deliverable test-able.

## Phase 1 — Backend foundation (~12h)

### Task 1.1 — `apps/accounts` scaffold + models (2h)
- Tạo app `apps/accounts/` (apps.py, admin.py, __init__.py)
- Add vào `LOCAL_APPS` ở settings
- Models: `User` (extends AbstractBaseUser + PermissionsMixin), `Role`, `Permission`
- `UserManager` (custom create_user, create_superuser)
- `__str__` cho 3 model
- **Deliverable**: `python manage.py makemigrations accounts` tạo 0001_initial sạch, model import được trong shell.

### Task 1.2 — Reset dev DB + migrate fresh (1h)
- Backup dev DB (`pg_dump`) trước (an toàn)
- Set `AUTH_USER_MODEL = 'accounts.User'` ở settings/base.py
- Drop + recreate `pim_dev` database
- Run `python manage.py migrate` từ đầu (core extensions → accounts → catalog → skus)
- **Deliverable**: `python manage.py migrate` clean, DB sạch, FK ở catalog/skus/core ref `accounts_users.id`.

### Task 1.3 — `seed_initial_data` management command (1.5h)
- Tạo 20 permission code (từ personas.md matrix)
- Tạo 6 role, gán permission theo matrix
- Tạo `smoke` superuser với role `super_admin`
- Tạo 5 test user (1 per non-super role) với mật khẩu `testpass`
- Tạo 3 sample product + 6 sample variant (matrix 2 material × 3 color × 1 size)
- Idempotent (chạy lại không lỗi, dùng get_or_create)
- **Deliverable**: `python manage.py seed_initial_data` thành công, login smoke + 5 role user qua Django Admin.

### Task 1.4 — JWT claims encoding (1h)
- Subclass `CustomRefreshToken` thêm `role`, `permissions` vào payload
- Unit test: decode JWT thấy đầy đủ claims
- **Deliverable**: `CustomRefreshToken.for_user(user)` trả token có claim đúng.

### Task 1.5 — `CookieJWTAuthentication` (1.5h)
- Đọc `access_token` từ cookie, validate signature
- Check `user.is_active`, raise nếu False
- Gắn `request._jwt_claims = validated.payload`
- **Deliverable**: request kèm cookie hợp lệ → `request.user.is_authenticated = True`.

### Task 1.6 — `HasPermission` class + wire vào viewsets (2h)
- `HasPermission(perm_code)` permission class
- `ProductViewSet.get_permissions()` map action → perm_code
- Tương tự `VariantViewSet`, `ProductVariantMatrixView`
- **Deliverable**: cashier (perm chỉ `order:*`) gọi `POST /products/` trả 403.

### Task 1.7 — Auth views (login, refresh, logout, me) (2h)
- `LoginView`: set 2 httpOnly cookies + csrftoken cookie
- `RefreshView`: đọc refresh từ cookie, set lại access cookie
- `LogoutView`: blacklist refresh + delete cookies
- `MeView`: trả user + role + permissions
- Error response shape consistent: `{error_code, message}`
- **Deliverable**: tất cả 4 endpoint cURL test pass (smoke login → me → refresh → logout flow).

### Task 1.8 — `apps/accounts/tests/` (3h)
- factories: UserFactory, RoleFactory, PermissionFactory với traits cho 6 role
- conftest: fixtures `super_admin_client`, `catalog_manager_client`, ... (force_authenticate + set cookie)
- test_models.py: User unique username/email, Role permissions M2M
- test_services_auth.py: login success/fail, refresh, logout blacklist
- test_jwt_claims.py: claims encode đầy đủ, deactivate user → reject
- test_permissions.py: HasPermission logic isolated
- test_api_auth.py: 4 endpoint integration
- test_permission_matrix.py: parametrize 6 role × 5 action × 3 viewset → expected 200/201/204 hoặc 403
- **Deliverable**: pytest pass ≥ 95% coverage cho `apps/accounts/`.

## Phase 2 — Frontend (~10h)

### Task 2.1 — `lib/api/auth.ts` + types (1h)
- `login(username, password)`, `logout()`, `refresh()`, `getMe()`
- Types: `User`, `Role`, `Permission`
- **Deliverable**: hover trong VS Code thấy đầy đủ type.

### Task 2.2 — `axios` config cookie + CSRF + refresh interceptor (1.5h)
- `withCredentials: true`, `xsrfCookieName: 'csrftoken'`, `xsrfHeaderName: 'X-CSRFToken'`
- Response 401 interceptor → POST `/auth/refresh/` → retry (lock concurrent refresh)
- Refresh 401 → redirect `/login`
- **Deliverable**: manual test: login → wait access expire → trigger API → tự refresh + retry trong DevTools Network.

### Task 2.3 — `useAuth` hook + `lib/auth/permissions.ts` (1.5h)
- `useAuth()` query `/auth/me/`, staleTime infinity, invalidate sau login/logout
- `hasPermission(perms, code)` helper
- `usePermission(code)` hook trả boolean
- **Deliverable**: render `useAuth().data.role` ở admin page.

### Task 2.4 — `middleware.ts` route guard (1h)
- Match `/admin/:path*`, `/pos/:path*`
- Check `access_token` cookie tồn tại → next, không thì redirect `/login?next=...`
- **Deliverable**: truy cập `/admin/products` chưa login → redirect `/login?next=/admin/products`.

### Task 2.5 — Login page refactor (1.5h)
- Form gọi `login(username, password)` (qua axios với withCredentials)
- Sau success: invalidate `useAuth` query → fetch `/me/` → redirect theo role (super_admin/manager → /admin/products, cashier → /pos)
- Handle error 401: show message tiếng Việt
- **Deliverable**: login flow happy path + invalid creds error message.

### Task 2.6 — `<PermissionGuard>` component + apply (1h)
- Component: `<PermissionGuard perm="product:create" fallback={null}>{children}</>`
- Wrap nút "Tạo product" trên list page, "Xoá" trên detail page
- Tương tự cho variant
- **Deliverable**: cashier login thấy list product nhưng không thấy nút "Tạo mới" / "Xoá".

### Task 2.7 — Logout button (0.5h)
- Header có nút "Đăng xuất" → gọi `logout()` → invalidate auth query → redirect `/login`
- **Deliverable**: click logout → cookie xoá (DevTools), redirect.

### Task 2.8 — FE tests (2h)
- Vitest: schema test cho login zod, hook test `useAuth` với MSW
- MSW handlers: `/auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/me/`
- Playwright: matrix 2 role (super_admin login full access, cashier login bị guard ở `/admin/products` create button hidden)
- **Deliverable**: tests pass; tổng FE test count tăng ≥ 20.

## Phase 3 — Finalize (~5h)

### Task 3.1 — ADR cho User swap (0.5h)
- `docs/architecture/adr/0001-custom-user-model.md`
- Quyết định, lý do, alternatives, consequences
- **Deliverable**: ADR commit.

### Task 3.2 — Append BR-011 → BR-014 vào `business-rules.md` (0.5h)
- BR-011 (token TTL), BR-012 (JWT claims invalidate), BR-013 (deactivate reject), BR-014 (logout blacklist)
- **Deliverable**: file updated.

### Task 3.3 — code-review BE + FE (1.5h)
- Run skill code-review trên 2 batch
- Fix Critical/Major nếu có
- **Deliverable**: ✅ Approve.

### Task 3.4 — Commit + CHANGELOG + CLAUDE.md status update (1h)
- BE commit: `feat(accounts): add custom User + RBAC + JWT cookie auth`
- FE commit: `feat(accounts): add cookie-based auth + middleware guard + PermissionGuard`
- Docs commit: ADR + business-rules + CHANGELOG + status
- **Deliverable**: 3 commit pushed lên `main`.

### Task 3.5 — Smoke test manual (1.5h)
- Login smoke → /admin/products → /admin/products/:id/variants → tạo variant → logout
- Login cashier (tạo bằng Django Admin) → /admin/products → button "Tạo mới" ẩn, POST trả 403
- Refresh flow: edit token cookie exp về quá khứ trong DevTools → trigger request → tự refresh + retry
- **Deliverable**: 3 scenario pass, screenshot/log ghi vào CHANGELOG.

## Definition of Done

- [ ] 8 BE task + 8 FE task + 5 finalize đều ✅
- [ ] BE coverage `apps/accounts/` ≥ 95%
- [ ] FE typecheck + lint clean
- [ ] 12 AC từ SPEC đều test pass
- [ ] Permission matrix test 6 × N pass
- [ ] code-review ✅ Approve (0 Critical/Major)
- [ ] CHANGELOG + ADR + business-rules + status update đều committed
- [ ] Smoke manual 3 scenario pass

## Risks revisit

| Risk | Mitigation status |
|---|---|
| User model swap migration | Task 1.2 backup DB trước + reverse migration noop ok cho dev |
| CSRF + cookie complexity | Task 2.2 dùng axios xsrf built-in, không tự code |
| Refresh race 2 tab | Task 2.2 lock `refreshPromise` singleton |
| JWT claim stale (đổi role) | Acceptable 15m delay đã ghi BR-012 |
| smoke lockout sau migration | Task 1.3 idempotent + check cuối migrate |
