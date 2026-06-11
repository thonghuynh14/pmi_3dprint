import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  useCreateVariant,
  useCreateVariantMatrix,
  useDeleteVariant,
  useRestoreVariant,
  useUpdateVariant,
  useVariant,
  useVariants,
} from "@/lib/hooks/use-variants";
import { server } from "@/test/msw/server";

// Mock toast — không cần Toaster mount trong test.
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const PRODUCT_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// ===========================================================================
// Queries
// ===========================================================================
describe("useVariants", () => {
  it("fetches variant list from API", async () => {
    const { result } = renderHook(() => useVariants(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(2);
    expect(result.current.data?.results[0].sku).toBe("DRAGON-PLA-RED-M-01");
  });

  it("filters by search param (server-side)", async () => {
    const { result } = renderHook(() => useVariants({ search: "blue" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(1);
    expect(result.current.data?.results[0].color_code3).toBe("BLU");
  });
});

describe("useVariant", () => {
  it("does not fetch when id is null", () => {
    const { result } = renderHook(() => useVariant(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("fetches single variant by id", async () => {
    const { result } = renderHook(() => useVariant("v-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("v-1");
    expect(result.current.data?.material_name).toBe("PLA");
  });
});

// ===========================================================================
// Mutations: Create
// ===========================================================================
describe("useCreateVariant", () => {
  const validPayload = {
    product_id: PRODUCT_ID,
    material_name: "PLA",
    material_code3: "PLA",
    color_name: "Red",
    color_code3: "RED",
    size_preset: "M",
    base_price: 150000,
    status: "draft" as const,
    attributes: {},
  };

  it("creates variant successfully", async () => {
    const { result } = renderHook(() => useCreateVariant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(validPayload);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("new-variant-id");
    expect(result.current.data?.material_code3).toBe("PLA");
  });

  it("surfaces SkuLengthInvalid error (detail-dict shape)", async () => {
    const { result } = renderHook(() => useCreateVariant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ ...validPayload, material_code3: "TOOLONG" });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("handles 500 server error gracefully", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/skus/variants/", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useCreateVariant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(validPayload);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ===========================================================================
// Mutations: Update
// ===========================================================================
describe("useUpdateVariant", () => {
  it("updates base_price + status (mutable fields)", async () => {
    const { result } = renderHook(() => useUpdateVariant("v-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ base_price: 200000, status: "archived" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.base_price).toBe("200000");
    expect(result.current.data?.status).toBe("archived");
  });

  it("rejects immutable field change (material_code3)", async () => {
    // Cast vì variantUpdateSchema strip key này → ta gửi thẳng cho API.
    server.use(
      http.patch(
        "http://localhost:8000/api/v1/skus/variants/v-1/",
        async () =>
          HttpResponse.json(
            {
              detail: {
                detail: "Field material_code3 là immutable, không update được.",
                field: "material_code3",
              },
            },
            { status: 400 },
          ),
      ),
    );

    const { result } = renderHook(() => useUpdateVariant("v-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ base_price: 100 });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ===========================================================================
// Mutations: Delete + Restore
// ===========================================================================
describe("useDeleteVariant + useRestoreVariant", () => {
  it("soft-deletes variant (204)", async () => {
    const { result } = renderHook(() => useDeleteVariant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("v-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("restores variant", async () => {
    const { result } = renderHook(() => useRestoreVariant(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("v-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.deleted_at).toBeNull();
  });
});

// ===========================================================================
// Mutations: Matrix bulk
// ===========================================================================
describe("useCreateVariantMatrix", () => {
  it("creates 4 variants for 2×2×1 matrix", async () => {
    const { result } = renderHook(() => useCreateVariantMatrix(PRODUCT_ID), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      materials: [
        { name: "PLA", code3: "PLA" },
        { name: "ABS", code3: "ABS" },
      ],
      colors: [
        { name: "Red", code3: "RED" },
        { name: "Blue", code3: "BLU" },
      ],
      sizes: ["M"],
      base_price: 150000,
      status: "draft",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.count).toBe(4);
    expect(result.current.data?.created).toHaveLength(4);
    expect(result.current.data?.created[0].sku).toBe(
      "DRAGON-PLA-RED-M-01",
    );
  });

  it("surfaces BatchTooLarge (detail-dict) when > 100", async () => {
    // Override để BE chắc chắn trả 400 dạng detail-dict.
    server.use(
      http.post(
        `http://localhost:8000/api/v1/catalog/products/${PRODUCT_ID}/variants/bulk-matrix/`,
        () =>
          HttpResponse.json(
            {
              detail: {
                detail: "Vượt giới hạn 121/100 variants mỗi batch.",
                requested: 121,
                max: 100,
              },
            },
            { status: 400 },
          ),
      ),
    );

    const { result } = renderHook(() => useCreateVariantMatrix(PRODUCT_ID), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      materials: [{ name: "PLA", code3: "PLA" }],
      colors: [{ name: "Red", code3: "RED" }],
      sizes: ["M"],
      base_price: 100,
      status: "draft",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
