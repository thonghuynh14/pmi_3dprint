import { http, HttpResponse } from "msw";

import type {
  Product,
  ProductListItem,
  ProductListResponse,
} from "@/lib/types/product";

// Khớp baseURL của apiClient: NEXT_PUBLIC_API_URL default "http://localhost:8000/api"
// → axios baseURL "http://localhost:8000/api/v1".
const BASE = "http://localhost:8000/api/v1";

function makeListItem(overrides: Partial<ProductListItem> = {}): ProductListItem {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Dragon Figure",
    slug: "dragon-figure",
    sku_root: "DRAGON",
    status: "active",
    brand: "",
    tags: ["figure"],
    updated_at: "2026-05-26T10:00:00+07:00",
    deleted_at: null,
    ...overrides,
  };
}

function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    ...makeListItem(),
    short_description: "",
    long_description: "",
    attributes: {},
    created_at: "2026-05-26T09:00:00+07:00",
    created_by: { id: 1, username: "smoke" },
    updated_by: { id: 1, username: "smoke" },
    deleted_by: null,
    ...overrides,
  } as Product;
}

export const handlers = [
  // LIST
  http.get(`${BASE}/catalog/products/`, ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";

    const all: ProductListItem[] = [
      makeListItem({ id: "p-1", name: "Dragon Figure", sku_root: "DRAGON" }),
      makeListItem({ id: "p-2", name: "Phone Case", sku_root: "PHCASE" }),
    ];
    const results = search
      ? all.filter(
          (p) =>
            p.name.toLowerCase().includes(search) ||
            p.sku_root.toLowerCase().includes(search),
        )
      : all;

    const body: ProductListResponse = {
      count: results.length,
      next: null,
      previous: null,
      results,
    };
    return HttpResponse.json(body);
  }),

  // CREATE
  http.post(`${BASE}/catalog/products/`, async ({ request }) => {
    const payload = (await request.json()) as Record<string, unknown>;
    const skuRoot = String(payload.sku_root ?? "");

    // Giả lập conflict cho sku_root đặc biệt.
    if (skuRoot.toUpperCase() === "DUPLIC") {
      return HttpResponse.json(
        { detail: "Mã sku_root đã tồn tại (case-insensitive)." },
        { status: 409 },
      );
    }

    return HttpResponse.json(
      makeProduct({
        id: "new-product-id",
        name: String(payload.name ?? ""),
        sku_root: skuRoot.toUpperCase(),
        slug: String(payload.slug || "auto-generated-slug"),
      }),
      { status: 201 },
    );
  }),
];
