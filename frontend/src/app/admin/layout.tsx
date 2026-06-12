"use client";

/**
 * Admin shell layout.
 *
 * Auth bootstrap qua useAuth() (gọi GET /auth/me/). Middleware đã guard
 * tầng cookie trước khi render — vào đây access_token cookie chắc chắn
 * có. useAuth fetch metadata user (name, role, permissions) cho UI.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useAuth, useLogout } from "@/lib/hooks/use-auth";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { data, isLoading } = useAuth();
  const logoutMutation = useLogout();

  function handleLogout() {
    logoutMutation.mutate(undefined, {
      onSettled: () => {
        // Idempotent: BE clear cookies dù logout fail.
        router.replace("/login");
      },
    });
  }

  if (isLoading) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">
        Loading...
      </div>
    );
  }

  const username = data?.user.username ?? "";
  const role = data?.user.role ?? "";

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
        <div className="flex items-center gap-3 text-sm">
          {username && (
            <span className="text-muted-foreground">
              {username}
              {role && (
                <span className="ml-2 rounded bg-muted px-2 py-0.5 font-mono text-xs">
                  {role}
                </span>
              )}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
          >
            Đăng xuất
          </Button>
        </div>
      </header>
      <main className="flex-1 bg-muted/20">{children}</main>
    </div>
  );
}
