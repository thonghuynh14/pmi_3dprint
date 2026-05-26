/**
 * Next.js middleware skeleton.
 *
 * MVP: cho phép qua hết. Feature auth sẽ:
 *   - Check JWT access token, redirect /(auth)/login nếu chưa login
 *   - Route guard theo role (cashier không vào /(admin)/...)
 *
 * i18n routing (vi/en) sẽ thêm khi feature i18n triển khai.
 */
import { NextResponse, type NextRequest } from "next/server";

export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match mọi route TRỪ:
     * - api/* (BE call qua REST, không proxy ở FE)
     * - _next/static, _next/image, favicon.ico
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
