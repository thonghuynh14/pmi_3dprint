import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import {
  useAnyPermission,
  useAuth,
  useLogin,
  useLogout,
  usePermission,
} from "@/lib/hooks/use-auth";
import { server } from "@/test/msw/server";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useAuth", () => {
  it("fetches /me/ on mount, returns user + permissions", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.user.username).toBe("smoke");
    expect(result.current.data?.permissions).toContain("product:create");
  });

  it("handles 401 (no auth) without retry", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/auth/me/", () =>
        HttpResponse.json({ detail: "auth required" }, { status: 401 }),
      ),
    );
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useLogin", () => {
  it("successful login resolves with AuthUser", async () => {
    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ username: "catmgr", password: "pw" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.username).toBe("catmgr");
    expect(result.current.data?.role).toBe("catalog_manager");
  });

  it("surfaces 401 on invalid credentials", async () => {
    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ username: "ghost", password: "x" });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useLogout", () => {
  it("logout mutation succeeds", async () => {
    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

// ---------------------------------------------------------------------------
// Permission hooks (composed with useAuth)
// ---------------------------------------------------------------------------
describe("usePermission", () => {
  it("returns true cho permission có trong /me/", async () => {
    const wrapper = createWrapper();
    const { result: authResult } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(authResult.current.isSuccess).toBe(true));

    const { result } = renderHook(() => usePermission("product:create"), {
      wrapper,
    });
    expect(result.current).toBe(true);
  });

  it("returns false khi /me/ chưa load (initial render)", () => {
    // useAuth chưa fire → undefined permissions → false.
    const { result } = renderHook(() => usePermission("product:create"), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBe(false);
  });
});

describe("useAnyPermission", () => {
  it("returns true khi any code present sau khi auth load", async () => {
    const wrapper = createWrapper();
    const { result: authResult } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(authResult.current.isSuccess).toBe(true));

    const { result } = renderHook(
      () => useAnyPermission(["product:create", "channel:publish"]),
      { wrapper },
    );
    expect(result.current).toBe(true);
  });
});
