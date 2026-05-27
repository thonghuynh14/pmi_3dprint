/**
 * zod schemas cho Product input (create + update).
 *
 * Mirror validation của BE `ProductInputSerializer` để fail fast ở FE
 * trước khi gửi network request. BE vẫn là source of truth — FE chỉ
 * tăng UX bằng validate sớm.
 */

import { z } from "zod";

import type { ProductStatus } from "@/lib/types/product";

const PRODUCT_STATUSES = ["draft", "active", "archived"] as const satisfies readonly ProductStatus[];

// Khớp regex BE serializer.
const SKU_ROOT_RE = /^[A-Z0-9]{3,8}$/;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ATTR_KEY_RE = /^[a-zA-Z0-9_-]+$/;

export const productInputSchema = z.object({
  name: z
    .string()
    .min(1, "Tên không được trống.")
    .max(200, "Tên tối đa 200 ký tự."),

  // slug optional: rỗng → BE auto-generate từ name (python-slugify).
  slug: z
    .string()
    .max(220, "Slug tối đa 220 ký tự.")
    .refine((v) => v === "" || SLUG_RE.test(v), {
      message: "Slug phải lowercase ascii + số, phân cách bằng dấu gạch nối.",
    })
    .default(""),

  // sku_root: FE cho user nhập bất kỳ case, BE upper. Validate format
  // sau khi upper để feedback đúng.
  sku_root: z
    .string()
    .min(3, "sku_root tối thiểu 3 ký tự.")
    .max(8, "sku_root tối đa 8 ký tự.")
    .refine((v) => SKU_ROOT_RE.test(v.toUpperCase()), {
      message: "sku_root chỉ chữ và số (A-Z, 0-9).",
    }),

  status: z.enum(PRODUCT_STATUSES).default("draft"),

  short_description: z.string().default(""),
  long_description: z.string().default(""),
  brand: z.string().max(100, "Brand tối đa 100 ký tự.").default(""),

  tags: z
    .array(z.string().min(1).max(64, "Mỗi tag tối đa 64 ký tự."))
    .max(50, "Tối đa 50 tags.")
    .default([]),

  attributes: z
    .record(z.string(), z.unknown())
    .refine(
      (obj) => Object.keys(obj).every((k) => ATTR_KEY_RE.test(k)),
      { message: "Attribute key chỉ accept chữ/số/_/-." },
    )
    .default({}),
});

export type ProductInput = z.infer<typeof productInputSchema>;

/** Update accept partial — RHF dirty fields only sẽ gửi field thay đổi. */
export const productUpdateSchema = productInputSchema.partial();
export type ProductUpdateInput = z.infer<typeof productUpdateSchema>;
