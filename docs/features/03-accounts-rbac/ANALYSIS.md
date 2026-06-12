# Feature Analysis: Accounts / RBAC (Standard scope)

## Summary

Foundational auth + 6-role RBAC để mở hệ thống cho team 6-10 người thật. Gỡ 4 deferred items đã tích từ feature 01-02 (token storage XSS, refresh flow chưa hoạt, middleware guard, viewset permission).

## Problem Statement

Hiện tại app đang ở trạng thái "dev login": bất cứ user nào (kể cả qua POS Cashier) login vào đều full quyền như super_admin. Cụ thể:

- **`smoke/smokepass`** là superuser duy nhất, dev share account cho người dùng thử qua ngrok demo
- **Access token ở `localStorage`** → XSS risk; XSS có thể đánh cắp token + impersonate
- **Refresh flow** chỉ wire 1 nửa: login lấy access nhưng `/auth/refresh/` interceptor chưa hoạt → access hết 15 phút phải re-login
- **Route guard** chỉ client-side trong `admin/layout.tsx` → page flash + bypass được nếu disable JS
- **Viewset permission** chỉ `IsAuthenticated`, không phân biệt role: Cashier xoá được Product, Channel Operator publish được mà không bị chặn

**Persona pain (từ personas.md):**
- Anh Hùng (Catalog Manager): không nên có quyền publish lên marketplace (Channel Operator phụ trách)
- Chị Lan (Production Manager): cần xem cost_price nhưng KHÔNG được sửa giá bán
- Chị Hoa (Cashier): chỉ truy cập POS, KHÔNG sửa được SP/giá

→ Không gỡ blocker này thì **không thể mở multi-user thật** — chỉ demo solo qua ngrok với người tin tưởng.

## MVP Alignment

- [x] In MVP scope (PRD.md đề cập 6 roles + permission matrix là core)
- [x] Aligns với primary goal (internal tool team 6-10 người)
- [x] Không conflict với "Out of Scope" (Supabase Auth — đã chốt dùng Django auth, Pattern A)

## Impact

- **Reach**: 100% users (foundational — mọi role đều cần đăng nhập + phân quyền)
- **Importance**: **Critical** (blocker cho multi-user demo, security risk nếu deploy)
- **Confidence**: **High** (deferred items đã tích từ feature 01-02 với mitigation note rõ ràng, persona pain + permission matrix có sẵn ở `docs/product/personas.md`)

## Scope (Standard cut, đã chốt với user)

### Trong scope ✅
1. **`apps/accounts` app**: custom `User` model (extends AbstractUser) thêm field `role` (FK Role).
2. **Role + Permission model**: 6 role (super_admin, catalog_manager, production_manager, channel_operator, designer, cashier) + 20 permission code từ `personas.md`.
3. **Migration swap `AUTH_USER_MODEL`** sang `accounts.User`. Dev DB sẽ phải reset (data fixtures + smoke user re-seed).
4. **JWT refresh rotation + httpOnly cookie** cho refresh token. Access token vẫn ở memory (Zustand) nhưng có interceptor auto-refresh.
5. **Middleware route guard** ở Next.js: redirect `/login` nếu không có access; redirect home nếu role không có quyền vào route.
6. **Viewset permission classes**: wire `HasPermission('product:create')` vào tất cả viewsets hiện tại (Product + Variant + matrix).
7. **Quản lý role assignment** qua Django Admin (super_admin gán role cho user).
8. **Tests**: permission matrix test (mỗi role × mỗi endpoint → expected status), refresh flow, route guard.

### Out of scope ❌ (defer)
- UI quản lý user CRUD ở web (super_admin tạo/sửa user qua Django Admin, không có web UI riêng)
- Object-level permission (django-guardian) — chỉ role-level, đủ cho team nhỏ
- 2FA / OTP / SSO
- Password reset qua email (super_admin reset trong Django Admin)
- Audit log riêng cho auth events (đã có core AuditLog, ghi action `auth.login_failed` ở service)
- Session timeout idle (chỉ JWT TTL 15min)

## Effort estimate

| Layer | Effort | Detail |
|---|---|---|
| BE — accounts app + User swap | 6h | Custom User + Role + Permission model + migration data |
| BE — RBAC permission classes | 3h | `HasPermission`, wire vào 3 ViewSet hiện có + smoke test |
| BE — refresh flow + cookie | 3h | Login set httpOnly cookie, refresh endpoint từ cookie |
| FE — middleware guard | 3h | `middleware.ts` check token + role permission per route |
| FE — auth refactor | 5h | Zustand store, in-memory access, axios interceptor refresh |
| FE — login + 401 handling | 2h | Error toast, redirect login khi refresh expires |
| Test — BE permission matrix | 3h | 6 role × 5 endpoint = 30 cases, parametrize |
| Test — FE auth flow | 2h | Vitest hook test + Playwright login refresh |
| Docs | 1h | CHANGELOG, ADR cho User swap |
| **Total** | **~28h** | **L effort** (~3-4 ngày dev) |

## Alternatives considered

- **Option A — Thin (chỉ httpOnly cookie + middleware, defer RBAC)**: rejected. Vẫn không cho multi-role mở thật được; chỉ giải quyết XSS, không giải quyết permission. Refactor RBAC sau sẽ phải đụng lại viewset → đẩy nợ kỹ thuật.
- **Option B — Full (Standard + UI CRUD user)**: rejected. UI quản lý user không phải pain ngay (super_admin chỉ tạo 5-10 user 1 lần qua Django Admin). Tăng effort thêm ~8h cho lợi ích nhỏ.
- **Option C — django-guardian (object-level perm)**: rejected. Team 6-10 người, mỗi role có scope rõ ràng — role-level đủ. Object-level chỉ cần khi multi-tenant.
- **Option D — Defer feature 03, làm `design-files` trước**: rejected. design-files sẽ cần Designer role để upload (BR-003 wire vào variant); nếu chưa có RBAC thì lại phải patch quyền sau khi đã ship.

## Risks

1. **Migration swap `AUTH_USER_MODEL`**: Django docs cảnh báo "significant undertaking" sau khi có data. Dev DB sẽ phải reset (acceptable — chỉ có `smoke` user + ~10 product/variant test). Production chưa có data nên không lo.
   - **Mitigation**: làm migration plan rõ ràng, document ADR; backup dev DB trước.
2. **JWT in httpOnly cookie + CSRF**: cookie auto-send → cần CSRF token cho POST/PATCH/DELETE.
   - **Mitigation**: dùng SameSite=Strict + Origin check; DRF có sẵn CSRF middleware optional.
3. **Refresh token rotation race**: 2 tab cùng refresh có thể blacklist token của nhau.
   - **Mitigation**: simplejwt có `BLACKLIST_AFTER_ROTATION` + grace period; document edge case.
4. **Permission check N+1**: mỗi request load user.role.permissions → N+1.
   - **Mitigation**: cache permission set trong JWT claims (encoded khi login).
5. **Smoke user mất quyền sau migration**: nếu seed role chưa chạy → super_admin lockout.
   - **Mitigation**: post-migration management command `seed_roles_and_assign_smoke`.

## Recommendation

**🟢 BUILD NOW**

**Reasoning**:
- Critical importance + 100% reach + high confidence (đã có persona + perm matrix sẵn)
- Blocker thật sự cho mở multi-user (không build → mọi feature tiếp theo đều patch quyền sau)
- Deferred items tích càng nhiều càng đắt fix (đã 2 feature tích thành 4 items)
- Effort L (~28h) hợp lý cho impact strategic
- Risk lớn nhất (User swap migration) controllable vì dev DB reset được, prod chưa có data

## Next steps

→ **Đợi user confirm "build now"** trước khi vào PHA 2 (SPEC/DESIGN/TASKS)

PHA 2 sẽ chốt:
- User flow login → refresh → logout → role-based redirect
- Acceptance criteria 6 roles × 5 endpoint (permission matrix)
- Migration strategy chi tiết (reset dev DB hay data migration)
- Token storage decision cuối (cookie vs in-memory cho access)
- File layout `apps/accounts/` + `frontend/src/lib/auth/`
