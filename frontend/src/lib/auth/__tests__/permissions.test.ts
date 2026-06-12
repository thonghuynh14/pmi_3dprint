import { describe, expect, it } from "vitest";

import {
  hasAllPermissions,
  hasAnyPermission,
  hasPermission,
} from "@/lib/auth/permissions";

describe("hasPermission", () => {
  it("returns true when code present", () => {
    expect(hasPermission(["product:create", "product:read"], "product:create")).toBe(
      true,
    );
  });

  it("returns false when code missing", () => {
    expect(hasPermission(["product:read"], "product:create")).toBe(false);
  });

  it("returns false when permissions undefined (chưa load)", () => {
    expect(hasPermission(undefined, "product:create")).toBe(false);
  });

  it("returns false for empty list", () => {
    expect(hasPermission([], "product:create")).toBe(false);
  });
});

describe("hasAnyPermission", () => {
  it("returns true when at least 1 code present", () => {
    expect(
      hasAnyPermission(["variant:read"], ["product:create", "variant:read"]),
    ).toBe(true);
  });

  it("returns false when none present", () => {
    expect(hasAnyPermission(["order:read"], ["product:create", "variant:read"])).toBe(
      false,
    );
  });

  it("returns false when required list empty", () => {
    expect(hasAnyPermission(["product:read"], [])).toBe(false);
  });
});

describe("hasAllPermissions", () => {
  it("returns true when all codes present", () => {
    expect(
      hasAllPermissions(
        ["product:create", "product:update", "product:delete"],
        ["product:create", "product:update"],
      ),
    ).toBe(true);
  });

  it("returns false when at least 1 missing", () => {
    expect(
      hasAllPermissions(["product:create"], ["product:create", "product:update"]),
    ).toBe(false);
  });

  it("returns true for empty required (vacuous truth)", () => {
    expect(hasAllPermissions(["product:read"], [])).toBe(true);
  });
});
