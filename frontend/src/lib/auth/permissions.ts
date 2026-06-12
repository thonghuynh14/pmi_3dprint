/**
 * Permission helpers (client-side check).
 *
 * Mirror BE permission code matrix ở `personas.md`. Dùng cho UI conditional
 * rendering (vd ẩn nút "Tạo mới" khi user không có `product:create`).
 *
 * **Lưu ý**: FE check chỉ là UX guard, KHÔNG phải security. BE
 * `ActionPermission` luôn enforce — nếu user bypass FE thì BE vẫn trả 403.
 */

import type { PermissionCode } from "@/lib/types/auth";

/** super_admin = bypass mọi check (chuẩn Django). */
export const SUPER_ADMIN_ROLE = "super_admin";

export function hasPermission(
  userPermissions: readonly PermissionCode[] | undefined,
  required: PermissionCode,
): boolean {
  if (!userPermissions) return false;
  return userPermissions.includes(required);
}

export function hasAnyPermission(
  userPermissions: readonly PermissionCode[] | undefined,
  required: readonly PermissionCode[],
): boolean {
  if (!userPermissions) return false;
  return required.some((code) => userPermissions.includes(code));
}

export function hasAllPermissions(
  userPermissions: readonly PermissionCode[] | undefined,
  required: readonly PermissionCode[],
): boolean {
  if (!userPermissions) return false;
  return required.every((code) => userPermissions.includes(code));
}
