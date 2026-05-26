# Auth Pattern (JWT + Refresh)

## Strategy

- Backend Django DRF cấp JWT (access + refresh) qua `dj-rest-auth` hoặc `djangorestframework-simplejwt`.
- Access token: short-lived (15 phút), lưu memory hoặc httpOnly cookie.
- Refresh token: long-lived (7-30 ngày), httpOnly cookie (an toàn hơn localStorage).
- Next.js middleware kiểm tra cookie + redirect nếu chưa auth.

## Middleware

```ts
// src/middleware.ts
import { NextResponse, type NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password'];
const POS_PATHS = ['/pos'];
const ADMIN_PATHS = ['/products', '/variants', '/design-files', '/materials', '/printers', '/poc', '/channels', '/orders'];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const refreshToken = req.cookies.get('refresh_token')?.value;
  const userRole = req.cookies.get('user_role')?.value; // signed cookie hoặc fetch /me
  
  // Public paths
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    if (refreshToken) {
      return NextResponse.redirect(new URL('/products', req.url));
    }
    return NextResponse.next();
  }
  
  // Protected: must have refresh token
  if (!refreshToken) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // Role check
  if (POS_PATHS.some(p => pathname.startsWith(p)) && !['cashier', 'super_admin'].includes(userRole ?? '')) {
    return NextResponse.redirect(new URL('/403', req.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

## Auth provider

```tsx
// src/components/providers/auth-provider.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api/auth';

interface User {
  id: string;
  email: string;
  role: 'super_admin' | 'catalog_manager' | 'production_manager' | 'channel_operator' | 'designer' | 'cashier';
  permissions: string[];
}

interface AuthContextValue {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (perm: string) => boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  
  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);
  
  const login = async (email: string, password: string) => {
    const { user } = await authApi.login(email, password);
    setUser(user);
    router.push('/products');
  };
  
  const logout = async () => {
    await authApi.logout();
    setUser(null);
    router.push('/login');
  };
  
  const hasPermission = (perm: string) => user?.permissions.includes(perm) ?? false;
  
  return (
    <AuthContext.Provider value={{ user, login, logout, hasPermission, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
```

## Permission-aware UI

```tsx
// components/auth/can.tsx
'use client';

import { useAuth } from '@/components/providers/auth-provider';

export function Can({ permission, children, fallback = null }: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission } = useAuth();
  return <>{hasPermission(permission) ? children : fallback}</>;
}

// Usage:
<Can permission="channel.publish">
  <Button>Publish to Shopee</Button>
</Can>
```
