import { http, HttpResponse } from "msw";

import type {
  Product,
  ProductListItem,
  ProductListResponse,
} from "@/lib/types/product";
import type {
  Variant,
  VariantListItem,
  VariantListResponse,
  VariantMatrixResponse,
} from "@/lib/types/variant";

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

  // ==========================================================================
  // VARIANTS
  // ==========================================================================
  ...variantHandlers(),
];

// ---------------------------------------------------------------------------
// Variant fixtures + handlers
// ---------------------------------------------------------------------------
function makeVariantListItem(
  overrides: Partial<VariantListItem> = {},
): VariantListItem {
  return {
    id: "v-1",
    sku: "DRAGON-PLA-RED-M-01",
    name: "Dragon Figure - PLA Red M",
    sequence_no: 1,
    material_code3: "PLA",
    color_code3: "RED",
    size_preset: "M",
    base_price: "150000.00",
    status: "active",
    updated_at: "2026-05-26T10:00:00+07:00",
    deleted_at: null,
    ...overrides,
  };
}

function makeVariant(overrides: Partial<Variant> = {}): Variant {
  return {
    id: "v-1",
    sku: "DRAGON-PLA-RED-M-01",
    sequence_no: 1,
    name: "Dragon Figure - PLA Red M",
    product_id: "p-1",
    product_name: "Dragon Figure",
    material_name: "PLA",
    material_code3: "PLA",
    color_name: "Red",
    color_code3: "RED",
    size_preset: "M",
    base_price: "150000.00",
    cost_price: "40000.00",
    status: "active",
    attributes: {},
    created_at: "2026-05-26T09:00:00+07:00",
    updated_at: "2026-05-26T10:00:00+07:00",
    deleted_at: null,
    created_by: { id: 1, username: "smoke" },
    updated_by: { id: 1, username: "smoke" },
    deleted_by: null,
    ...overrides,
  };
}

function variantHandlers() {
  return [
    // LIST
    http.get(`${BASE}/skus/variants/`, ({ request }) => {
      const url = new URL(request.url);
      const search = url.searchParams.get("search")?.toLowerCase() ?? "";

      const all: VariantListItem[] = [
        makeVariantListItem({ id: "v-1", color_code3: "RED" }),
        makeVariantListItem({
          id: "v-2",
          sku: "DRAGON-PLA-BLU-M-02",
          name: "Dragon Figure - PLA Blue M",
          sequence_no: 2,
          color_code3: "BLU",
        }),
      ];
      const results = search
        ? all.filter(
            (v) =>
              v.sku.toLowerCase().includes(search) ||
              v.name.toLowerCase().includes(search),
          )
        : all;

      const body: VariantListResponse = {
        count: results.length,
        next: null,
        previous: null,
        results,
      };
      return HttpResponse.json(body);
    }),

    // RETRIEVE
    http.get(`${BASE}/skus/variants/:id/`, ({ params }) => {
      return HttpResponse.json(makeVariant({ id: String(params.id) }));
    }),

    // CREATE
    http.post(`${BASE}/skus/variants/`, async ({ request }) => {
      const payload = (await request.json()) as Record<string, unknown>;
      const matCode3 = String(payload.material_code3 ?? "PLA").toUpperCase();

      // Giả lập SkuLengthInvalidError dạng dict detail (BE override __init__).
      if (matCode3 === "TOOLONG") {
        return HttpResponse.json(
          {
            detail: {
              detail: "Độ dài SKU vượt quá giới hạn (24 ký tự).",
              length: 25,
              max: 24,
            },
          },
          { status: 400 },
        );
      }

      return HttpResponse.json(
        makeVariant({
          id: "new-variant-id",
          sku: `DRAGON-${matCode3}-RED-M-01`,
          material_code3: matCode3,
        }),
        { status: 201 },
      );
    }),

    // PARTIAL UPDATE
    http.patch(`${BASE}/skus/variants/:id/`, async ({ params, request }) => {
      const payload = (await request.json()) as Record<string, unknown>;

      // Immutable field guard (BE serializer.validate).
      const immutable = [
        "product_id",
        "material_code3",
        "color_code3",
        "size_preset",
      ];
      const violated = immutable.find((f) => f in payload);
      if (violated) {
        return HttpResponse.json(
          {
            detail: {
              detail: `Field ${violated} là immutable, không update được.`,
              field: violated,
            },
          },
          { status: 400 },
        );
      }

      return HttpResponse.json(
        makeVariant({
          id: String(params.id),
          ...(typeof payload.base_price === "string" ||
          typeof payload.base_price === "number"
            ? { base_price: String(payload.base_price) }
            : {}),
          ...(payload.status ? { status: payload.status as Variant["status"] } : {}),
        }),
      );
    }),

    // SOFT DELETE
    http.delete(`${BASE}/skus/variants/:id/`, () => {
      return new HttpResponse(null, { status: 204 });
    }),

    // RESTORE
    http.post(`${BASE}/skus/variants/:id/restore/`, ({ params }) => {
      return HttpResponse.json(
        makeVariant({ id: String(params.id), deleted_at: null }),
      );
    }),

    // MATRIX BULK
    http.post(
      `${BASE}/catalog/products/:productId/variants/bulk-matrix/`,
      async ({ params, request }) => {
        const payload = (await request.json()) as {
          materials: { name: string; code3: string }[];
          colors: { name: string; code3: string }[];
          sizes: string[];
          base_price: string | number;
        };
        const total =
          payload.materials.length * payload.colors.length * payload.sizes.length;

        // BE BatchTooLargeError → detail dict.
        if (total > 100) {
          return HttpResponse.json(
            {
              detail: {
                detail: `Vượt giới hạn ${total}/100 variants mỗi batch.`,
                requested: total,
                max: 100,
              },
            },
            { status: 400 },
          );
        }

        const created: Variant[] = [];
        let seq = 1;
        for (const m of payload.materials) {
          for (const c of payload.colors) {
            for (const s of payload.sizes) {
              created.push(
                makeVariant({
                  id: `v-bulk-${seq}`,
                  sku: `DRAGON-${m.code3}-${c.code3}-${s}-${seq
                    .toString()
                    .padStart(2, "0")}`,
                  sequence_no: seq,
                  product_id: String(params.productId),
                  material_name: m.name,
                  material_code3: m.code3,
                  color_name: c.name,
                  color_code3: c.code3,
                  size_preset: s,
                  base_price: String(payload.base_price),
                }),
              );
              seq += 1;
            }
          }
        }

        const body: VariantMatrixResponse = {
          count: created.length,
          created,
        };
        return HttpResponse.json(body, { status: 201 });
      },
    ),
  ];
}
