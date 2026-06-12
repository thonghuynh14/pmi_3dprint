/**
 * Auth hooks: useAuth() + mutations (login/logout) + permission helpers.
 *
 * useAuth() là single source of truth ở client cho user hiện tại. Cookie
 * httpOnly chứa JWT — FE không decode token; thay vào đó gọi `/auth/me/`
 * để lấy user + permissions. Cache vĩnh viễn (staleTime=Infinity) cho
 * tới khi login/logout invalidate manual.
 *
 * Nếu request 401 / refresh fail → axios interceptor đã redirect /login
 * (xem lib/api/client.ts). Hook chỉ cần handle "loading / authenticated /
 * error" — không cần custom redirect logic.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import {
  getMe,
  login as apiLogin,
  logout as apiLogout,
} from "@/lib/api/auth";
import {
  hasAllPermissions,
  hasAnyPermission,
  hasPermission,
} from "@/lib/auth/permissions";
import type { MeResponse, PermissionCode } from "@/lib/types/auth";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const authKeys = {
  me: ["auth", "me"] as const,
};

// ---------------------------------------------------------------------------
// useAuth — fetch /auth/me/ once, cache forever
// ---------------------------------------------------------------------------
export function useAuth(
  options?: Pick<UseQueryOptions<MeResponse>, "enabled" | "initialData">,
) {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: getMe,
    // Cache cho tới khi login/logout invalidate manual.
    staleTime: Infinity,
    // 401 đã được axios interceptor xử (refresh hoặc redirect /login) —
    // không cần retry query.
    retry: false,
    ...options,
  });
}

// ---------------------------------------------------------------------------
// useLogin / useLogout mutations
// ---------------------------------------------------------------------------
export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiLogin(username, password),
    onSuccess: () => {
      // Sau login: invalidate cache → useAuth refetch /me/ lấy permissions.
      qc.invalidateQueries({ queryKey: authKeys.me });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: apiLogout,
    onSuccess: () => {
      // Xoá toàn bộ query cache khi logout — tránh leak data sang user kế tiếp.
      qc.clear();
    },
  });
}

// ---------------------------------------------------------------------------
// Permission hooks (UX guard)
// ---------------------------------------------------------------------------

/** True nếu user hiện tại có permission code này.
 *
 * Trả false khi data chưa load / user chưa login. Component dùng để
 * conditional render — KHÔNG phải security gate (BE luôn enforce). */
export function usePermission(code: PermissionCode): boolean {
  const { data } = useAuth();
  return hasPermission(data?.permissions, code);
}

export function useAnyPermission(codes: readonly PermissionCode[]): boolean {
  const { data } = useAuth();
  return hasAnyPermission(data?.permissions, codes);
}

export function useAllPermissions(codes: readonly PermissionCode[]): boolean {
  const { data } = useAuth();
  return hasAllPermissions(data?.permissions, codes);
}
