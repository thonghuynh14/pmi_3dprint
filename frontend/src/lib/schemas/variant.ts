/**
 * Zod schemas cho Variant input.
 *
 * Mirror validation BE (apps/skus/serializers/variants.py + utils.py).
 * BE vẫn là source of truth — FE chỉ tăng UX bằng validate sớm.
 *
 * 3 schema:
 * - `variantInputSchema`        single create (POST /skus/variants/)
 * - `variantUpdateSchema`       partial update — chỉ 4 field mutable
 * - `variantMatrixInputSchema`  matrix bulk (POST /catalog/products/<id>/variants/bulk-matrix/)
 */

import { z } from "zod";

import type { VariantStatus } from "@/lib/types/variant";

const VARIANT_STATUSES = [
  "draft",
  "active",
  "archived",
] as const satisfies readonly VariantStatus[];

// Match regex BE serializer.
const CODE3_RE = /^[A-Z0-9]{2,4}$/;
const SIZE_PRESET_RE = /^[A-Za-z0-9]{1,8}$/;
const ATTR_KEY_RE = /^[a-zA-Z0-9_-]+$/;

/** BE-side cap matrix batch (utils.MAX_BATCH). */
export const MAX_VARIANT_BATCH = 100;

/** code3 — uppercase 2-4 alphanumeric. Accept lowercase input (BE upper). */
export const code3Schema = z
  .string()
  .min(2, "code3 tối thiểu 2 ký tự.")
  .max(4, "code3 tối đa 4 ký tự.")
  .refine((v) => CODE3_RE.test(v.toUpperCase()), {
    message: "code3 chỉ chấp nhận chữ và số (A-Z, 0-9).",
  });

/** size_preset — 1-8 alphanumeric (cho phép "12cm", giữ nguyên case). */
export const sizePresetSchema = z
  .string()
  .min(1, "size_preset không được trống.")
  .max(8, "size_preset tối đa 8 ký tự.")
  .refine((v) => SIZE_PRESET_RE.test(v), {
    message: "size_preset chỉ alphanumeric (1-8 ký tự).",
  });

/** Axis entry — dùng trong matrix input cho materials + colors. */
export const axisEntrySchema = z.object({
  name: z
    .string()
    .min(1, "Tên không được trống.")
    .max(64, "Tên tối đa 64 ký tự."),
  code3: code3Schema,
});
export type AxisEntryInput = z.infer<typeof axisEntrySchema>;

const attributesSchema = z
  .record(z.string(), z.unknown())
  .refine(
    (obj) => Object.keys(obj).every((k) => ATTR_KEY_RE.test(k)),
    { message: "Attribute key chỉ accept chữ/số/_/-." },
  );

// ===========================================================================
// Single CRUD input
// ===========================================================================
export const variantInputSchema = z.object({
  product_id: z.string().uuid("product_id phải UUID hợp lệ."),
  material_name: z
    .string()
    .min(1, "Tên material không trống.")
    .max(64, "Tên material tối đa 64 ký tự."),
  material_code3: code3Schema,
  color_name: z
    .string()
    .min(1, "Tên color không trống.")
    .max(64, "Tên color tối đa 64 ký tự."),
  color_code3: code3Schema,
  size_preset: sizePresetSchema,
  base_price: z.coerce
    .number({ message: "Giá bán phải là số." })
    .nonnegative("Giá bán ≥ 0."),
  cost_price: z.coerce
    .number({ message: "Cost phải là số." })
    .nonnegative("Cost ≥ 0.")
    .nullable()
    .optional(),
  status: z.enum(VARIANT_STATUSES).default("draft"),
  attributes: attributesSchema.default({}),
});
export type VariantInput = z.infer<typeof variantInputSchema>;

// ===========================================================================
// Partial update — chỉ 4 field mutable (match BE VariantUpdateSerializer)
// ===========================================================================
export const variantUpdateSchema = z.object({
  base_price: z.coerce
    .number({ message: "Giá bán phải là số." })
    .nonnegative("Giá bán ≥ 0.")
    .optional(),
  cost_price: z.coerce
    .number({ message: "Cost phải là số." })
    .nonnegative("Cost ≥ 0.")
    .nullable()
    .optional(),
  status: z.enum(VARIANT_STATUSES).optional(),
  attributes: attributesSchema.optional(),
});
export type VariantUpdateInput = z.infer<typeof variantUpdateSchema>;

// ===========================================================================
// Matrix bulk input
// ===========================================================================
export const variantMatrixInputSchema = z
  .object({
    materials: z
      .array(axisEntrySchema)
      .min(1, "Cần ≥ 1 material."),
    colors: z
      .array(axisEntrySchema)
      .min(1, "Cần ≥ 1 color."),
    sizes: z
      .array(sizePresetSchema)
      .min(1, "Cần ≥ 1 size."),
    base_price: z.coerce
      .number({ message: "Giá bán phải là số." })
      .nonnegative("Giá bán ≥ 0."),
    cost_price: z.coerce
      .number({ message: "Cost phải là số." })
      .nonnegative("Cost ≥ 0.")
      .nullable()
      .optional(),
    status: z.enum(VARIANT_STATUSES).default("draft"),
  })
  .refine(
    (d) =>
      d.materials.length * d.colors.length * d.sizes.length <=
      MAX_VARIANT_BATCH,
    {
      message: `Tổng variants vượt giới hạn ${MAX_VARIANT_BATCH}/batch.`,
    },
  );
export type VariantMatrixInput = z.infer<typeof variantMatrixInputSchema>;
