import { expect, test } from "@playwright/test";

/**
 * E2E matrix flow: login → tạo product → vào variants → matrix 2×2×1 → 4 variants.
 *
 * Cố ý tách khỏi products.spec.ts (matrix là feature riêng, dài hơn). Cleanup
 * product cuối test để chạy lặp không tích rác.
 *
 * sku_root unique theo timestamp tránh BR-001 collision (case-insensitive).
 * YÊU CẦU runtime: Docker up + superuser `smoke/smokepass` trong dev DB.
 */

const SUFFIX = String(Date.now()).slice(-5);
const SKU_ROOT = `V${SUFFIX}`; // "V" + 5 số = 6 ký tự
const NAME = `Variant E2E ${SUFFIX}`;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill("smoke");
  await page.getByLabel("Mật khẩu").fill("smokepass");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL("**/admin/products");
}

test("matrix bulk creator: 2×2×1 → 4 variants", async ({ page }) => {
  await login(page);

  // --- Tạo product để gắn variants ---
  await page.getByRole("link", { name: /Tạo mới/ }).click();
  await page.waitForURL("**/admin/products/new");
  await page.getByLabel(/Tên sản phẩm/).fill(NAME);
  await page.getByLabel(/SKU root/).fill(SKU_ROOT);
  await page.getByRole("button", { name: "Tạo product" }).click();
  await page.waitForURL("**/admin/products");

  // --- Vào product detail → variants ---
  await page.getByRole("link", { name: NAME, exact: true }).click();
  await page.waitForURL(/\/admin\/products\/[^/?]+$/);
  await page.getByRole("link", { name: "Quản lý variants" }).click();
  await page.waitForURL(/\/admin\/products\/[^/]+\/variants$/);

  // --- Vào matrix form ---
  await page.getByRole("link", { name: /Thêm matrix/ }).click();
  await page.waitForURL(/\/variants\/new-matrix$/);

  // --- Thêm 2 materials qua Enter (tránh ambiguous "Thêm" button) ---
  await page.getByPlaceholder("Tên (Polylactic Acid)").fill("PLA");
  await page.getByPlaceholder("Code (PLA)").fill("PLA");
  await page.getByPlaceholder("Code (PLA)").press("Enter");
  await expect(page.getByText("PLA", { exact: false }).first()).toBeVisible();

  await page.getByPlaceholder("Tên (Polylactic Acid)").fill("ABS");
  await page.getByPlaceholder("Code (PLA)").fill("ABS");
  await page.getByPlaceholder("Code (PLA)").press("Enter");

  // --- Thêm 2 colors ---
  await page.getByPlaceholder("Tên (Red)").fill("Red");
  await page.getByPlaceholder("Code (RED)").fill("RED");
  await page.getByPlaceholder("Code (RED)").press("Enter");

  await page.getByPlaceholder("Tên (Red)").fill("Blue");
  await page.getByPlaceholder("Code (RED)").fill("BLU");
  await page.getByPlaceholder("Code (RED)").press("Enter");

  // --- Thêm 1 size ---
  await page.getByPlaceholder("Vd M, L, XL hoặc 12cm").fill("M");
  await page.getByPlaceholder("Vd M, L, XL hoặc 12cm").press("Enter");

  // --- Pricing ---
  await page.getByLabel(/Giá bán \(VND\)/).fill("150000");

  // --- Total counter hiển thị 4 ---
  await expect(page.getByText(/Sẽ tạo.*4.*variants/)).toBeVisible();

  // --- Preview ---
  await page.getByRole("button", { name: /Preview \(4\)/ }).click();
  await expect(
    page.getByRole("heading", { name: /Sẽ tạo 4 variants/ }),
  ).toBeVisible();

  // Preview table có 4 row + header → 5 row tổng.
  // Đếm theo content body row (skip header).
  const previewRows = page.locator("table tbody tr");
  await expect(previewRows).toHaveCount(4);

  // --- Submit ---
  await page.getByRole("button", { name: /Tạo 4 variants/ }).click();

  // --- Redirect về list, có 4 variant ---
  await page.waitForURL(/\/variants$/);
  const listRows = page.locator("table tbody tr");
  await expect(listRows).toHaveCount(4);

  // --- Cleanup product (CASCADE soft-delete variants luôn) ---
  await page.goto("/admin/products");
  const row = page.getByRole("row").filter({ hasText: NAME });
  await row.getByRole("button", { name: "Hành động" }).click();
  await page.getByRole("menuitem", { name: /Xoá/ }).click();
  await page.getByRole("button", { name: "Xoá", exact: true }).click();
});
