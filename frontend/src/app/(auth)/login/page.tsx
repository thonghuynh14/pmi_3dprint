"use client";

/**
 * Login page (cookie-based).
 *
 * POST /auth/login/ → BE set httpOnly cookies (access + refresh + csrf).
 * FE không touch token; sau success, gọi /auth/me/ qua useAuth để lấy
 * permissions + role → redirect.
 *
 * Default redirect: /admin/products. Cashier POS sẽ defer riêng.
 * URL param `?next=...` cùng-origin có ưu tiên.
 */

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "@/lib/hooks/use-auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/admin/products";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const loginMutation = useLogin();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loginMutation.mutate(
      { username, password },
      {
        onSuccess: (user) => {
          toast.success(`Chào ${user.full_name || user.username}`);
          // router.replace cần "next" cùng origin để tránh open redirect.
          const target = next.startsWith("/") ? next : "/admin/products";
          router.replace(target);
        },
        onError: (error) => {
          const err = error as { response?: { data?: { detail?: string } } };
          toast.error(
            err.response?.data?.detail ??
              "Đăng nhập thất bại. Kiểm tra lại tài khoản.",
          );
        },
      },
    );
  }

  const submitting = loginMutation.isPending;

  return (
    <div className="grid min-h-screen place-items-center bg-muted/30 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border bg-card p-6 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold">Đăng nhập</h1>
          <p className="text-sm text-muted-foreground">
            3D Printing PIM — quản lý sản phẩm & SKU đa kênh
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Mật khẩu</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
        </Button>
      </form>
    </div>
  );
}

// useSearchParams() yêu cầu Suspense boundary cho static prerender
// (Next.js CSR bailout). Wrap LoginForm.
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
