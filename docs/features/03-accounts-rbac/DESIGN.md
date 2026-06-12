# Design: Accounts / RBAC

## Component breakdown

### Backend — `apps/accounts/`

```
apps/accounts/
├── __init__.py
├── apps.py
├── admin.py
├── models.py                    # User (AbstractUser+role), Role, Permission
├── managers.py                  # UserManager (custom)
├── authentication.py            # CookieJWTAuthentication (đọc từ cookie)
├── permissions.py               # HasPermission(perm_code) class
├── serializers/
│   ├── __init__.py
│   ├── auth.py                  # LoginInput, RegisterInput (nếu cần), TokenOutput
│   └── user.py                  # UserSerializer (output, slim)
├── services/
│   ├── __init__.py
│   └── auth.py                  # auth_login, auth_refresh, auth_logout
├── views/
│   ├── __init__.py
│   ├── auth.py                  # LoginView, RefreshView, LogoutView, CsrfView
│   └── me.py                    # /me/ endpoint trả profile + role + perms
├── jwt_utils.py                 # encode_with_claims, decode helpers
├── exceptions.py                # InvalidCredentials, PermissionDenied (đã có DRF nhưng wrap để error_code consistent)
├── urls.py
├── management/commands/
│   └── seed_roles.py            # Tạo 6 role + 20 permission code + gán smoke = super_admin
├── migrations/
│   ├── 0001_initial.py          # Tạo User + Role + Permission models
│   └── 0002_migrate_auth_user_data.py  # Data migration: auth_user → accounts_user
└── tests/
    ├── factories.py
    ├── conftest.py
    ├── test_models.py
    ├── test_services_auth.py
    ├── test_jwt_claims.py
    ├── test_permissions.py
    ├── test_api_auth.py
    └── test_permission_matrix.py   # parametrize 6 role × N endpoint
```

### Frontend — Auth refactor

```
frontend/src/
├── middleware.ts                ← THÊM/SỬA: check access_token cookie
├── app/
│   └── (auth)/
│       └── login/
│           └── page.tsx          ← SỬA: POST /auth/login/ (cookie-based)
├── lib/
│   ├── api/
│   │   ├── client.ts             ← SỬA: withCredentials=true, X-CSRFToken header, refresh interceptor
│   │   └── auth.ts               ← MỚI: login(), logout(), refresh(), getMe()
│   ├── auth/
│   │   ├── permissions.ts        ← MỚI: type Permission, hasPermission(claims, perm)
│   │   └── csrf.ts               ← MỚI: getCsrfToken() từ cookie
│   ├── hooks/
│   │   ├── use-auth.ts           ← MỚI: useAuth() trả {user, role, permissions, isLoading}
│   │   └── use-permission.ts     ← MỚI: usePermission('product:create') trả boolean
│   └── types/
│       └── auth.ts               ← MỚI: User, Role, Permission types
└── app/admin/
    └── _components/
        └── permission-guard.tsx  ← MỚI: <PermissionGuard perm="product:create">...</> wrap button/UI
```

## Data model

### `accounts.User`

```python
class User(AbstractBaseUser, PermissionsMixin):
    id = BigAutoField PK  # giữ kiểu cũ để compatible audit_log FK
    username = CharField(unique, 150)
    email = EmailField(unique)
    full_name = CharField(150, blank)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)   # Django Admin access
    is_superuser = BooleanField(default=False)
    role = ForeignKey(Role, on_delete=PROTECT, null=True)
    date_joined = DateTimeField(auto_now_add=True)
    last_login = DateTimeField(null=True)  # Django auto-update

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    objects = UserManager()
```

### `accounts.Role`

```python
class Role(models.Model):
    id = UUIDField PK
    code = SlugField(unique, 32)             # 'super_admin', 'catalog_manager', ...
    name = CharField(64)
    description = TextField(blank)
    permissions = ManyToManyField(Permission, related_name='roles')
    created_at = DateTimeField(auto_now_add)
    
    class Meta:
        db_table = 'accounts_roles'
```

### `accounts.Permission`

```python
class Permission(models.Model):
    id = UUIDField PK
    code = SlugField(unique, 64)              # 'product:create', 'variant:cost_read'
    description = CharField(255)
    
    class Meta:
        db_table = 'accounts_permissions'
```

Seed 20 permission từ `personas.md` matrix:
```
product:create / read / update / delete
variant:price_read / price_update / cost_read
design_file:upload / set_license
poc:create
material:manage
printer:manage
channel:publish / credentials / price_override
order:read / create_pos
audit_log:read
user:manage
idea:create / promote
```

## Migration plan (Reset DB + seed)

Đã đổi từ data migration sang reset do gotcha `AUTH_USER_MODEL` swap với migration history (Django docs warn explicitly).

### Step 1 — Build apps/accounts với User/Role/Permission

`apps/accounts/migrations/0001_initial.py` (Django auto-gen):
- Create `accounts_users` (giống schema `auth_user` + `role_id` + `full_name`)
- Create `accounts_roles`, `accounts_permissions`, m2m `accounts_role_permissions`

### Step 2 — Set `AUTH_USER_MODEL` = 'accounts.User'

`settings/base.py`:
```python
AUTH_USER_MODEL = 'accounts.User'
```

Vì các migration cũ ở `catalog/skus/core` dùng `settings.AUTH_USER_MODEL` swappable_dependency (lazy-resolve), khi chạy fresh migration tất cả FK sẽ tự ref `accounts_users.id` đúng. **KHÔNG cần ALTER FK migration**.

### Step 3 — Reset dev DB + migrate fresh

```powershell
# Backup trước cho an toàn
docker compose exec postgres pg_dump -U pim_user pim_dev > backup_pre_accounts.sql

# Drop + recreate
docker compose exec postgres psql -U pim_user -d postgres -c "DROP DATABASE pim_dev"
docker compose exec postgres psql -U pim_user -d postgres -c "CREATE DATABASE pim_dev OWNER pim_user"

# Migrate fresh
python manage.py migrate
```

### Step 4 — Seed data

`apps/accounts/management/commands/seed_initial_data.py`:
```python
class Command(BaseCommand):
    help = "Seed roles, permissions, smoke user + sample catalog data (dev only)"
    
    def handle(self, *args, **kwargs):
        # 1. Tạo 20 Permission
        perms = {code: Permission.objects.get_or_create(code=code, description=DESC[code])[0] 
                 for code in PERMS}
        # 2. Tạo 6 Role + gán permissions
        roles = {}
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = Role.objects.get_or_create(code=role_code, defaults={'name': ROLE_NAMES[role_code]})[0]
            role.permissions.set([perms[c] for c in perm_codes])
            roles[role_code] = role
        # 3. Tạo smoke = super_admin
        if not User.objects.filter(username='smoke').exists():
            User.objects.create_superuser(
                username='smoke', email='smoke@dev.local', password='smokepass',
                role=roles['super_admin'],
            )
        # 4. (optional) Tạo 1 user per role để test
        for role_code in ['catalog_manager', 'production_manager', 'channel_operator', 'designer', 'cashier']:
            User.objects.get_or_create(
                username=f'{role_code}_test',
                defaults={'email': f'{role_code}@dev.local', 'role': roles[role_code], 'is_active': True},
            )[0].set_password('testpass'); ...  # save với password
        # 5. Sample catalog data: 3 product + 6 variant (matrix 2x3x1)
        # ... gọi services.product_create + variant_bulk_create_matrix
        self.stdout.write(self.style.SUCCESS('✓ Seeded.'))
```

Run: `python manage.py seed_initial_data`

## JWT payload

```json
{
  "token_type": "access",
  "exp": 1718038200,
  "iat": 1718037300,
  "jti": "abc-123-uuid",
  "user_id": 1,
  "username": "smoke",
  "role": "super_admin",
  "permissions": ["product:create", "product:read", "user:manage", ...]
}
```

Subclass `simplejwt.RefreshToken`:
```python
class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token['username'] = user.username
        token['role'] = user.role.code if user.role else None
        token['permissions'] = (
            list(user.role.permissions.values_list('code', flat=True))
            if user.role else []
        )
        return token
```

## API contract

### `POST /api/v1/auth/login/`

```
Request body:
  { "username": "smoke", "password": "smokepass" }

Response 200:
  Body: { "user": {id, username, email, full_name, role: "super_admin"} }
  Cookies set:
    - access_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=900
    - refresh_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
    - csrftoken=<token>; Secure; SameSite=Lax; Path=/

Response 401:
  { "error_code": "INVALID_CREDENTIALS", "message": "Tên đăng nhập hoặc mật khẩu sai" }
```

### `POST /api/v1/auth/refresh/`

Đọc `refresh_token` từ cookie, set lại cookie `access_token` mới.

### `POST /api/v1/auth/logout/`

Blacklist refresh + delete cookies.

### `GET /api/v1/auth/me/`

Trả thông tin user hiện tại + role + permissions (cho FE bootstrap UI):
```
{ "user": {id, username, email, full_name}, "role": "...", "permissions": [...] }
```

## Permission class

```python
# apps/accounts/permissions.py
class HasPermission(permissions.BasePermission):
    """Check permission code có trong JWT claims không."""
    def __init__(self, perm_code: str):
        self.perm_code = perm_code
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        claims = getattr(request, '_jwt_claims', {})
        return self.perm_code in claims.get('permissions', [])


# Helper factory
def perm(code):
    return type(f'HasPermission_{code}', (HasPermission,), {})(code)
```

Wire vào ViewSet:
```python
# apps/catalog/views/product.py
class ProductViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        action_perm_map = {
            'list': 'product:read', 'retrieve': 'product:read',
            'create': 'product:create', 'partial_update': 'product:update',
            'destroy': 'product:delete', 'restore': 'product:update',
        }
        return [HasPermission(action_perm_map[self.action])]
```

## CookieJWTAuthentication

```python
# apps/accounts/authentication.py
class CookieJWTAuthentication(JWTAuthentication):
    """Đọc access_token từ cookie thay vì Authorization header."""
    def authenticate(self, request):
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        validated = self.get_validated_token(raw_token)
        user = self.get_user(validated)
        if not user.is_active:
            raise AuthenticationFailed('User deactivated', code='user_inactive')
        # Gắn claims vào request để permission class đọc
        request._jwt_claims = validated.payload
        return (user, validated)
```

## Frontend

### `middleware.ts`

```ts
import { NextRequest, NextResponse } from 'next/server';

const PROTECTED_PREFIX = ['/admin', '/pos'];

export function middleware(req: NextRequest) {
  const isProtected = PROTECTED_PREFIX.some(p => req.nextUrl.pathname.startsWith(p));
  if (!isProtected) return NextResponse.next();
  
  const access = req.cookies.get('access_token');
  if (!access) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('next', req.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/pos/:path*'],
};
```

### `lib/api/client.ts` thay đổi

```ts
export const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,             // browser tự gửi cookie
  xsrfCookieName: 'csrftoken',       // đọc CSRF cookie
  xsrfHeaderName: 'X-CSRFToken',     // gửi vào header
});

// Response interceptor: 401 → refresh → retry
let refreshPromise: Promise<void> | null = null;
apiClient.interceptors.response.use(undefined, async (error) => {
  if (error.response?.status !== 401 || error.config._retry) {
    return Promise.reject(error);
  }
  if (!refreshPromise) {
    refreshPromise = apiClient.post('/auth/refresh/').then(() => undefined)
      .finally(() => { refreshPromise = null; });
  }
  await refreshPromise;
  error.config._retry = true;
  return apiClient(error.config);
});
```

### `useAuth` hook

```ts
export function useAuth() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => apiClient.get('/auth/me/').then(r => r.data),
    staleTime: Infinity,        // Refetch khi invalidate manual (sau login/logout)
    retry: false,
  });
}
```

## Technical decisions (chose X over Y)

- **JWT in cookie thay vì Authorization header**: chốt với user — đỡ XSS, đơn giản FE (không phải Zustand store), đổi lại cần CSRF.
- **Permission ở JWT claims thay vì DB lookup**: O(1) check, không N+1. Trade-off: invalidation chậm tối đa 15m (acceptable, mọi UI write đều check permission lúc render → user thấy "Lưu" disable ngay).
- **Custom User model `BigAutoField` PK**: giữ kiểu cũ của `auth.User` để data migration không phải đổi FK type. Đa số bài tutorial khuyên dùng UUID PK cho User — không cần thiết, internal tool team nhỏ.
- **Data migration thay vì DB reset**: chốt với user.
- **Cookie SameSite=Lax thay vì Strict**: Lax cho phép cookie gửi khi navigate từ link → tốt cho deep link `/admin/products/abc`. Strict thì click link từ email cũng không gửi cookie → annoying.
- **Refresh token cookie Path=/api/v1/auth**: refresh token CHỈ gửi cho `/auth/*` endpoint → giảm bề mặt nếu access bị lộ.
- **Không dùng django-guardian**: role-level đủ cho team 6-10.
- **Permission code chuỗi `domain:action`**: human-readable trong JWT debug, dễ extend (vs số int).

## Out of scope (kỹ thuật)

- HTTPS enforce: dev `Secure=False`, prod `Secure=True` qua env var
- CORS: dùng proxy `/api/*` qua Next.js (cùng origin) → không cần CORS
- Rate limiting: defer (django-ratelimit khi đến lúc)
