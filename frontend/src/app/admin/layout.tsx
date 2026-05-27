"use client";

/**
 * Admin shell layout (placeholder).
 *
 * Tối thiểu: header + sidebar nav + logout. Khi feature `accounts/auth
 * UI` triển khai, thay bằng route protection (middleware check JWT)
 * + sidebar đa role + breadcrumbs.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  bootstrapAccessTokenFromStorage,
  getAccessToken,
  setAccessToken,
} from "@/lib/api/client";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  // Client-side guard: chưa có token → redirect login.
  useEffect(() => {
    bootstrapAccessTokenFromStorage();
    if (!getAccessToken()) {
      router.replace("/login?next=/admin/products");
      return;
    }
    setReady(true);
  }, [router]);

  function handleLogout() {
    setAccessToken(null);
    router.replace("/login");
  }

  if (!ready) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b bg-background px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/admin/products" className="text-lg font-semibold">
            3D Printing PIM
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link
              href="/admin/products"
              className="text-muted-foreground hover:text-foreground"
            >
              Products
            </Link>
          </nav>
        </div>
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          Đăng xuất
        </Button>
      </header>
      <main className="flex-1 bg-muted/20">{children}</main>
    </div>
  );
}
