# Spec: Accounts / RBAC

> Verdict 🟢 BUILD NOW — xem [ANALYSIS.md](ANALYSIS.md). Scope: Standard.

## Decisions đã chốt (PHA 2)

1. **Migration**: **Reset dev DB + seed script** (đổi từ "data migration" do gotcha Django `AUTH_USER_MODEL` swap với migration history — official docs khuyên avoid). Management command `seed_initial_data` tái tạo smoke + sample product/variant.
2. **Permission check**: encode `role` + `permissions: ['product:create', ...]` vào JWT claims; permission class đọc từ claims, KHÔNG DB hit
3. **Token storage**: cả access + refresh đều ở **httpOnly cookies**; CSRF token cho mutation; FE không cần Zustand auth store hay interceptor refresh phức tạp

## User flow

### Flow 1 — Login

```
1. User mở https://app.example.com → middleware check cookie "access_token"
   - Không có → redirect /login
   - Có nhưng expired → redirect /login (FE chỉ check exp, không decode signature)
2. User nhập username + password ở /login
3. FE POST /api/v1/auth/login/ (qua proxy)
   - BE: validate credentials, generate JWT(access TTL 15m, refresh TTL 7d)
   - JWT payload claim: { user_id, username, role, permissions: [...] }
   - Set 2 cookies httpOnly Secure SameSite=Lax:
     - access_token TTL 15m
     - refresh_token TTL 7d
   - Set csrftoken cookie (NON-httpOnly, FE đọc được, gửi qua header X-CSRFToken)
4. FE redirect về route mặc định theo role:
   - super_admin / catalog_manager / production_manager / channel_operator / designer → /admin/products
   - cashier → /pos (defer, redirect /admin/products tạm)
```

### Flow 2 — Authenticated request

```
1. Browser tự gửi cookies (access_token + csrftoken)
2. FE axios: header X-CSRFToken = csrftoken cookie value (cho mutation: POST/PATCH/PUT/DELETE)
3. BE CookieJWTAuthentication đọc access_token từ cookie → validate signature → decode claims
4. BE Permission class HasPermission('product:create') đọc permissions array từ request.user._jwt_claims
5. Authorized → execute; not authorized → 403 {error_code: 'PERMISSION_DENIED', message: ...}
```

### Flow 3 — Refresh auto

```
1. Request bất kỳ trả 401 (access expired)
2. FE axios response interceptor:
   a. Lock concurrent refresh (1 refresh tại 1 thời điểm)
   b. POST /api/v1/auth/refresh/ (browser tự gửi refresh_token cookie)
   c. BE validate refresh → generate new access (giữ refresh hoặc rotate tuỳ config)
   d. Set lại cookie access_token mới
   e. Retry request gốc
3. Nếu refresh cũng 401 (refresh expired):
   - FE clear local state, redirect /login
```

### Flow 4 — Logout

```
1. User click "Đăng xuất"
2. FE POST /api/v1/auth/logout/
3. BE:
   a. Blacklist refresh_token (qua simplejwt token_blacklist app)
   b. Delete cookies (set Max-Age=0)
4. FE redirect /login
```

### Flow 5 — Role-based route protection

```
1. Middleware /admin/* check cookie access_token tồn tại + not exp
   - Không có / expired → /login
2. Layout server component check role:
   - cashier → 403 page "Khu vực chỉ dành cho admin"
   - other roles → render
3. Page-level: nếu cần granular check (vd /admin/users chỉ super_admin),
   server component check role claim → redirect / 403
```

## Acceptance Criteria

### AC-1: Login happy path

```
Given user "smoke" có role "super_admin" và mật khẩu "smokepass"
When user POST /api/v1/auth/login/ {"username": "smoke", "password": "smokepass"}
Then response 200 với body {"user": {...}, "role": "super_admin"}
And response set 3 cookies: access_token (httpOnly), refresh_token (httpOnly), csrftoken
And access_token JWT có claim "permissions" chứa "user:manage"
```

### AC-2: Login fail

```
Given không có user nào tên "ghost"
When user POST /api/v1/auth/login/ {"username": "ghost", "password": "x"}
Then response 401 với body {"error_code": "INVALID_CREDENTIALS"}
And không có cookie nào được set
```

### AC-3: Authenticated GET với perm

```
Given user "catalog_user" role "catalog_manager" đã login (có cookie access_token)
When user GET /api/v1/catalog/products/
Then response 200 với danh sách products
```

### AC-4: Permission denied

```
Given user "cashier_user" role "cashier" đã login
When user POST /api/v1/catalog/products/ {...}
Then response 403 với body {"error_code": "PERMISSION_DENIED", "required": "product:create"}
```

### AC-5: Refresh tự động

```
Given user đã login, access_token cookie hết hạn (15m), refresh_token còn hạn (7d)
When FE gọi GET /api/v1/catalog/products/
Then BE trả 401
And FE interceptor gọi POST /api/v1/auth/refresh/
And response set lại cookie access_token mới
And FE retry GET /products/, trả 200
```

### AC-6: Refresh hết hạn

```
Given access_token + refresh_token đều hết hạn
When FE gọi bất kỳ endpoint nào
Then BE trả 401 cho cả request gốc và /refresh/
And FE clear state + redirect /login
```

### AC-7: Logout

```
Given user đã login
When user POST /api/v1/auth/logout/
Then response 200
And response set cookies access_token + refresh_token với Max-Age=0
And refresh_token đó bị blacklist (gọi lại /refresh/ với token cũ trả 401)
```

### AC-8: CSRF protection

```
Given user đã login, có cookie csrftoken="abc123"
When user POST /api/v1/catalog/products/ KHÔNG có header X-CSRFToken
Then response 403 {"error_code": "CSRF_FAILED"}
```

### AC-9: Role redirect sau login

```
Given user "cashier1" role "cashier"
When user POST /auth/login/ thành công
Then FE redirect /pos (hoặc /admin/products nếu pos chưa có)

Given user "catalog1" role "catalog_manager"
When login thành công
Then FE redirect /admin/products
```

### AC-10: Middleware guard

```
Given user chưa login (không có cookie access_token)
When user truy cập https://app/admin/products
Then Next.js middleware redirect /login?next=/admin/products
```

### AC-11: Role bị thay đổi (token cũ vẫn còn hạn)

```
Given user "u1" login với role "catalog_manager" → JWT chứa perm "product:create"
And super_admin đổi role của u1 thành "cashier" qua Django Admin
When u1 vẫn dùng access_token cũ POST /api/v1/catalog/products/
Then request thành công (JWT claims chưa cập nhật → đây là trade-off đã chốt)
And sau khi access_token hết hạn (15m), refresh sẽ encode role mới → block
```

### AC-12: Permission matrix (parametrized test)

```
Given matrix permission_map = {
  super_admin: all-allowed,
  catalog_manager: [product:*, variant:*, design_file:*, idea:promote],
  production_manager: [poc:*, material:*, printer:*, variant:cost_read],
  channel_operator: [channel:*, order:read],
  designer: [idea:create, design_file:upload],
  cashier: [order:create_pos, order:read]
}
When mỗi role hit mỗi viewset action
Then status code = 200/201/204 nếu permission_map[role] cho phép
And status code = 403 nếu không
```

## Edge cases checklist

### General
- [x] Concurrent edit (đã ở feature 01-02, không liên quan trực tiếp)
- [x] Soft delete user → cookie cũ vẫn dùng được tới khi access hết → wait 15m hoặc blacklist sub claim
- [x] Audit log: ghi action `auth.login_success`, `auth.login_failed`, `auth.logout`
- [x] i18n: error message "PERMISSION_DENIED" → mã code, FE map sang VN

### Auth-specific
- [x] User đổi mật khẩu → invalidate all tokens (blacklist by user_id)
- [x] User bị deactivate (`is_active=False`) → reject login + 401 trên token còn hạn (validate `is_active` ở authenticate class)
- [x] Refresh rotation race: 2 tab cùng refresh — simplejwt blacklist sau rotation → tab nào chậm hơn sẽ 401, FE retry refresh lần nữa
- [x] Cookie SameSite=Lax: form POST từ origin khác KHÔNG gửi cookie → CSRF không qua được (defense in depth)
- [x] Logout không cookie / cookie expired → vẫn trả 200 (idempotent)

### Migration
- [x] Migration order: tạo `accounts.User` trước, sau đó update FK ở catalog/skus/core qua RunSQL `ALTER TABLE ... REFERENCES accounts_user`
- [x] Data migrate: copy `auth_user` → `accounts_user` giữ ID, sau đó update settings.AUTH_USER_MODEL
- [x] Rollback: backup dev DB trước migration; ADR document chi tiết

## Out of scope (defer)

- UI quản lý user CRUD ở web (qua Django Admin)
- Object-level permission (django-guardian)
- 2FA / OTP / SSO / OAuth social
- Password reset qua email
- Audit log riêng cho auth (đã có core AuditLog)
- Session timeout idle (chỉ JWT TTL)
- Rate limiting login (chống brute force) — defer feature `security-hardening`
- Cookie domain config cho subdomain (single domain trong MVP)
- POS-specific layout với role cashier auto-redirect — defer feature `pos-app`

## Dependencies

- Feature 01 (Product CRUD) — sẽ wire permission vào ProductViewSet
- Feature 02 (Variant CRUD) — sẽ wire permission vào VariantViewSet + matrix endpoint
- Storage `pg_dump` để backup dev DB trước migration

## Business rules (mới — sẽ append vào business-rules.md)

- **BR-011**: Access token TTL 15 phút, refresh token TTL 7 ngày. Refresh rotation BẬT (`ROTATE_REFRESH_TOKENS=True`). Blacklist sau rotation BẬT.
- **BR-012**: Role permissions encode vào JWT claims tại login → invalidate khi access hết (max 15m delay so với DB).
- **BR-013**: User deactivated (`is_active=False`) → reject mọi request kể cả token còn hạn (check trong authentication class).
- **BR-014**: Logout blacklist refresh token, xoá cookie. Access token có thể còn hạn nhưng FE đã không có cookie → coi như expired.
