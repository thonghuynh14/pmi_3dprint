import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useCreateProduct, useProducts } from "@/lib/hooks/use-products";
import { server } from "@/test/msw/server";

// sonner toast → no-op trong test (không cần Toaster mount).
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useProducts", () => {
  it("fetches product list from API", async () => {
    const { result } = renderHook(() => useProducts({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(2);
    expect(result.current.data?.results[0].name).toBe("Dragon Figure");
  });

  it("passes search param to API (server filters)", async () => {
    const { result } = renderHook(() => useProducts({ search: "phone" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(1);
    expect(result.current.data?.results[0].name).toBe("Phone Case");
  });
});

describe("useCreateProduct", () => {
  it("creates product successfully", async () => {
    const { result } = renderHook(() => useCreateProduct(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "New Product",
      sku_root: "NEWPRD",
      slug: "",
      status: "draft",
      short_description: "",
      long_description: "",
      brand: "",
      tags: [],
      attributes: {},
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("new-product-id");
    expect(result.current.data?.sku_root).toBe("NEWPRD");
  });

  it("surfaces 409 conflict error", async () => {
    const { result } = renderHook(() => useCreateProduct(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "Dup",
      sku_root: "DUPLIC",
      slug: "",
      status: "draft",
      short_description: "",
      long_description: "",
      brand: "",
      tags: [],
      attributes: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("handles 500 server error gracefully", async () => {
    // Override handler 1 lần để trả 500.
    server.use(
      http.post("http://localhost:8000/api/v1/catalog/products/", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useCreateProduct(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "X",
      sku_root: "ERR500",
      slug: "",
      status: "draft",
      short_description: "",
      long_description: "",
      brand: "",
      tags: [],
      attributes: {},
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
