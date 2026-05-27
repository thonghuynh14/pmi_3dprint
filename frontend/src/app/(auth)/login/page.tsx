"use client";

/**
 * Login page (dev affordance).
 *
 * Feature `accounts/auth UI` được defer (xem ANALYSIS OQ-2). Trang
 * này dùng simplejwt endpoint /api/v1/auth/token/ trực tiếp + lưu
 * access vào localStorage. Khi feature accounts ra mắt, replace bằng
 * proper login UI (httpOnly refresh, RBAC, social login).
 */

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient, setAccessToken } from "@/lib/api/client";

interface TokenResponse {
  access: string;
  refresh: string;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/admin/products";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const { data } = await apiClient.post<TokenResponse>("/auth/token/", {
        username,
        password,
      });
      setAccessToken(data.access);
      toast.success("Đăng nhập thành công");
      router.replace(next);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(
        err.response?.data?.detail ?? "Đăng nhập thất bại. Kiểm tra lại tài khoản.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-muted/30 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border bg-card p-6 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold">Đăng nhập</h1>
          <p className="text-sm text-muted-foreground">
            Dev login — dùng tài khoản Django superuser.
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
