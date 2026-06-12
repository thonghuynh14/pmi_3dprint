/**
 * Next.js middleware: route guard cho /admin/* và /pos/*.
 *
 * Logic đơn giản: nếu cookie `access_token` không có → redirect /login
 * kèm `?next=<original_path>`. Middleware KHÔNG decode JWT (Edge runtime
 * không có `crypto` Node) — chỉ check tồn tại. Token expired thì axios
 * interceptor sẽ refresh (server-set cookie mới) hoặc redirect login.
 *
 * Logged-in user vào /login → redirect về /admin/products.
 */
import { NextResponse, type NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/admin", "/pos"];
const ACCESS_COOKIE = "access_token";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const access = req.cookies.get(ACCESS_COOKIE);

  // /login khi đã login → đẩy về admin (tránh loop sau refresh).
  if (pathname === "/login" && access) {
    return NextResponse.redirect(new URL("/admin/products", req.url));
  }

  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!isProtected) {
    return NextResponse.next();
  }

  if (!access) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", pathname + req.nextUrl.search);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  /*
   * Match route cần guard. Bỏ qua:
   * - /api/* (proxy → Django, không cần guard)
   * - _next/static, _next/image, favicon.ico (assets)
   */
  matcher: ["/admin/:path*", "/pos/:path*", "/login"],
};
