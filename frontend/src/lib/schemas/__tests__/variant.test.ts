import { describe, expect, it } from "vitest";

import {
  MAX_VARIANT_BATCH,
  axisEntrySchema,
  code3Schema,
  sizePresetSchema,
  variantInputSchema,
  variantMatrixInputSchema,
  variantUpdateSchema,
} from "@/lib/schemas/variant";

// ---------------------------------------------------------------------------
// code3
// ---------------------------------------------------------------------------
describe("code3Schema", () => {
  it("accepts uppercase 3-letter code", () => {
    expect(code3Schema.safeParse("PLA").success).toBe(true);
  });

  it("accepts lowercase (BE upper)", () => {
    expect(code3Schema.safeParse("pla").success).toBe(true);
  });

  it("accepts 2-4 alphanumeric", () => {
    expect(code3Schema.safeParse("R1").success).toBe(true);
    expect(code3Schema.safeParse("ABCD").success).toBe(true);
  });

  it("rejects 1 char", () => {
    expect(code3Schema.safeParse("A").success).toBe(false);
  });

  it("rejects 5 chars", () => {
    expect(code3Schema.safeParse("ABCDE").success).toBe(false);
  });

  it("rejects special chars", () => {
    expect(code3Schema.safeParse("P-A").success).toBe(false);
    expect(code3Schema.safeParse("PL ").success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// size_preset
// ---------------------------------------------------------------------------
describe("sizePresetSchema", () => {
  it("accepts M, XL, 12cm", () => {
    expect(sizePresetSchema.safeParse("M").success).toBe(true);
    expect(sizePresetSchema.safeParse("XL").success).toBe(true);
    expect(sizePresetSchema.safeParse("12cm").success).toBe(true);
  });

  it("rejects empty", () => {
    expect(sizePresetSchema.safeParse("").success).toBe(false);
  });

  it("rejects > 8 chars", () => {
    expect(sizePresetSchema.safeParse("123456789").success).toBe(false);
  });

  it("rejects special chars", () => {
    expect(sizePresetSchema.safeParse("L-XL").success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// axisEntrySchema
// ---------------------------------------------------------------------------
describe("axisEntrySchema", () => {
  it("accepts valid name + code3", () => {
    expect(
      axisEntrySchema.safeParse({ name: "PLA", code3: "PLA" }).success,
    ).toBe(true);
  });

  it("rejects empty name", () => {
    expect(
      axisEntrySchema.safeParse({ name: "", code3: "PLA" }).success,
    ).toBe(false);
  });

  it("rejects bad code3", () => {
    expect(
      axisEntrySchema.safeParse({ name: "PLA", code3: "P" }).success,
    ).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// variantInputSchema (single create)
// ---------------------------------------------------------------------------
const validInput = {
  product_id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  material_name: "PLA",
  material_code3: "PLA",
  color_name: "Red",
  color_code3: "RED",
  size_preset: "M",
  base_price: 150000,
};

describe("variantInputSchema", () => {
  it("parses valid minimal input + defaults", () => {
    const result = variantInputSchema.safeParse(validInput);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.status).toBe("draft");
      expect(result.data.attributes).toEqual({});
      expect(result.data.cost_price).toBeUndefined();
    }
  });

  it("rejects invalid UUID product_id", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      product_id: "not-a-uuid",
    });
    expect(result.success).toBe(false);
  });

  it("rejects negative base_price", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      base_price: -1,
    });
    expect(result.success).toBe(false);
  });

  it("coerces base_price string to number", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      base_price: "150000",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.base_price).toBe(150000);
  });

  it("accepts null cost_price", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      cost_price: null,
    });
    expect(result.success).toBe(true);
  });

  it("rejects status not in enum", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      status: "published",
    });
    expect(result.success).toBe(false);
  });

  it("rejects attribute key with spaces", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      attributes: { "bad key": "v" },
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid attributes", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      attributes: { finish: "matte", food_safe: true },
    });
    expect(result.success).toBe(true);
  });

  it("rejects size_preset > 8 chars", () => {
    const result = variantInputSchema.safeParse({
      ...validInput,
      size_preset: "123456789",
    });
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// variantUpdateSchema (partial — only 4 mutable fields)
// ---------------------------------------------------------------------------
describe("variantUpdateSchema", () => {
  it("accepts empty (no field)", () => {
    expect(variantUpdateSchema.safeParse({}).success).toBe(true);
  });

  it("accepts partial base_price only", () => {
    const result = variantUpdateSchema.safeParse({ base_price: 200000 });
    expect(result.success).toBe(true);
  });

  it("accepts partial status only", () => {
    const result = variantUpdateSchema.safeParse({ status: "archived" });
    expect(result.success).toBe(true);
  });

  it("accepts null cost_price (clear value)", () => {
    const result = variantUpdateSchema.safeParse({ cost_price: null });
    expect(result.success).toBe(true);
  });

  it("rejects negative base_price", () => {
    const result = variantUpdateSchema.safeParse({ base_price: -1 });
    expect(result.success).toBe(false);
  });

  it("ignores unknown fields (zod strips, không reject)", () => {
    // BE serializer là layer chặn cứng immutable; schema FE chỉ validate 4 field.
    const result = variantUpdateSchema.safeParse({
      base_price: 100,
      material_code3: "PLA",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).not.toHaveProperty("material_code3");
    }
  });
});

// ---------------------------------------------------------------------------
// variantMatrixInputSchema
// ---------------------------------------------------------------------------
const validMatrix = {
  materials: [{ name: "PLA", code3: "PLA" }],
  colors: [{ name: "Red", code3: "RED" }],
  sizes: ["M"],
  base_price: 150000,
};

describe("variantMatrixInputSchema", () => {
  it("parses 1×1×1 matrix", () => {
    const result = variantMatrixInputSchema.safeParse(validMatrix);
    expect(result.success).toBe(true);
  });

  it("rejects empty materials", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      materials: [],
    });
    expect(result.success).toBe(false);
  });

  it("rejects empty colors", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      colors: [],
    });
    expect(result.success).toBe(false);
  });

  it("rejects empty sizes", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      sizes: [],
    });
    expect(result.success).toBe(false);
  });

  it("accepts 10×5×2 = 100 = MAX_VARIANT_BATCH boundary", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      materials: Array.from({ length: 10 }, (_, i) => ({
        name: `M${i}`,
        code3: `M${i.toString().padStart(2, "0")}`,
      })),
      colors: Array.from({ length: 5 }, (_, i) => ({
        name: `C${i}`,
        code3: `C${i.toString().padStart(2, "0")}`,
      })),
      sizes: ["S", "M"],
    });
    expect(result.success).toBe(true);
  });

  it("rejects total > MAX_VARIANT_BATCH (11×5×2 = 110)", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      materials: Array.from({ length: 11 }, (_, i) => ({
        name: `M${i}`,
        code3: `M${i.toString().padStart(2, "0")}`,
      })),
      colors: Array.from({ length: 5 }, (_, i) => ({
        name: `C${i}`,
        code3: `C${i.toString().padStart(2, "0")}`,
      })),
      sizes: ["S", "M"],
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toContain(
        String(MAX_VARIANT_BATCH),
      );
    }
  });

  it("rejects negative base_price in matrix", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      base_price: -100,
    });
    expect(result.success).toBe(false);
  });

  it("rejects axis entry with invalid code3", () => {
    const result = variantMatrixInputSchema.safeParse({
      ...validMatrix,
      materials: [{ name: "PLA", code3: "X" }],
    });
    expect(result.success).toBe(false);
  });
});
