import { describe, expect, it } from "vitest";

import { productInputSchema } from "@/lib/schemas/product";

describe("productInputSchema", () => {
  it("parses valid minimal input + applies defaults", () => {
    const result = productInputSchema.safeParse({
      name: "Dragon Figure",
      sku_root: "DRAGON",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.status).toBe("draft");
      expect(result.data.slug).toBe("");
      expect(result.data.tags).toEqual([]);
      expect(result.data.attributes).toEqual({});
      expect(result.data.brand).toBe("");
    }
  });

  it("rejects empty name", () => {
    const result = productInputSchema.safeParse({ name: "", sku_root: "DRAGON" });
    expect(result.success).toBe(false);
  });

  it("rejects sku_root shorter than 3 chars", () => {
    const result = productInputSchema.safeParse({ name: "X", sku_root: "ab" });
    expect(result.success).toBe(false);
  });

  it("rejects sku_root longer than 8 chars", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGONFIRE",
    });
    expect(result.success).toBe(false);
  });

  it("accepts lowercase sku_root (uppercased downstream)", () => {
    // Schema validate sau khi toUpperCase → "dragon" hợp lệ.
    const result = productInputSchema.safeParse({ name: "X", sku_root: "dragon" });
    expect(result.success).toBe(true);
  });

  it("rejects sku_root with special chars", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRA-GON",
    });
    expect(result.success).toBe(false);
  });

  it("rejects slug with spaces", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      slug: "has spaces",
    });
    expect(result.success).toBe(false);
  });

  it("accepts empty slug (BE auto-generates)", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      slug: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid status", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      status: "published",
    });
    expect(result.success).toBe(false);
  });

  it("rejects attribute key with spaces", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      attributes: { "bad key": "v" },
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid attribute keys", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      attributes: { scale: "1:10", weight_g: 120, "food-safe": true },
    });
    expect(result.success).toBe(true);
  });

  it("rejects more than 50 tags", () => {
    const result = productInputSchema.safeParse({
      name: "X",
      sku_root: "DRAGON",
      tags: Array.from({ length: 51 }, (_, i) => `tag${i}`),
    });
    expect(result.success).toBe(false);
  });
});
