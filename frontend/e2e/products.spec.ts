import { expect, test } from "@playwright/test";

/**
 * Happy path E2E cho Product CRUD: login → create → edit → delete.
 *
 * KHÔNG dùng search box trong flow điều hướng: debounce search
 * (router.replace ?search=) fire trễ 300ms, abort navigation của link
 * click → flake. Product mới luôn ở top list (sort updated_at desc) nên
 * click trực tiếp được.
 *
 * sku_root unique theo timestamp để chạy lặp không bị 409.
 * YÊU CẦU runtime: Docker up + superuser `smoke/smokepass` trong dev DB.
 */

const SUFFIX = String(Date.now()).slice(-5);
const SKU_ROOT = `E2E${SUFFIX}`; // "E2E" + 5 số = 8 ký tự
const NAME = `E2E Product ${SUFFIX}`;
const NAME_EDITED = `${NAME} EDITED`;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill("smoke");
  await page.getByLabel("Mật khẩu").fill("smokepass");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL("**/admin/products");
}

test("catalog manager full CRUD flow", async ({ page }) => {
  await login(page);

  // --- CREATE ---
  await page.getByRole("link", { name: /Tạo mới/ }).click();
  await page.waitForURL("**/admin/products/new");
  await page.getByLabel(/Tên sản phẩm/).fill(NAME);
  await page.getByLabel(/SKU root/).fill(SKU_ROOT);
  await page.getByRole("button", { name: "Tạo product" }).click();

  // Redirect về list; product mới ở top (updated_at desc).
  await page.waitForURL("**/admin/products");
  const nameLink = page.getByRole("link", { name: NAME, exact: true });
  await expect(nameLink).toBeVisible();

  // --- EDIT ---
  await nameLink.click();
  await page.waitForURL(/\/admin\/products\/[^/?]+$/);
  const nameField = page.getByLabel(/Tên sản phẩm/);
  await expect(nameField).toHaveValue(NAME);
  await nameField.fill(NAME_EDITED);
  await page.getByRole("button", { name: "Lưu thay đổi" }).click();

  await page.waitForURL("**/admin/products");
  const editedLink = page.getByRole("link", { name: NAME_EDITED, exact: true });
  await expect(editedLink).toBeVisible();

  // --- DELETE --- (scope action button vào đúng row)
  const row = page.getByRole("row").filter({ hasText: NAME_EDITED });
  await row.getByRole("button", { name: "Hành động" }).click();
  await page.getByRole("menuitem", { name: /Xoá/ }).click();
  await page.getByRole("button", { name: "Xoá", exact: true }).click();

  // Product biến mất khỏi list mặc định.
  await expect(editedLink).toBeHidden();
});
