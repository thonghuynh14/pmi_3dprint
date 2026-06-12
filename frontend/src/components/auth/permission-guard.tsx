"use client";

/**
 * Wrap UI cần permission. Hide hoặc thay bằng fallback nếu user không có quyền.
 *
 * Lưu ý: chỉ là UX guard — BE luôn enforce `ActionPermission`. Đừng dùng
 * để hide sensitive data: user mở DevTools sẽ vẫn thấy trong response BE.
 *
 * Example:
 *   <PermissionGuard perm="product:create">
 *     <Button>Tạo mới</Button>
 *   </PermissionGuard>
 */

import type { ReactNode } from "react";

import { useAnyPermission } from "@/lib/hooks/use-auth";
import type { PermissionCode } from "@/lib/types/auth";

interface SingleProps {
  perm: PermissionCode;
  perms?: never;
  fallback?: ReactNode;
  children: ReactNode;
}

interface AnyProps {
  perm?: never;
  perms: readonly PermissionCode[];
  fallback?: ReactNode;
  children: ReactNode;
}

type Props = SingleProps | AnyProps;

export function PermissionGuard(props: Props) {
  // Hook luôn gọi unconditionally — chuyển single perm thành array 1 element.
  const codes = props.perm ? [props.perm] : (props.perms ?? []);
  const allowed = useAnyPermission(codes);

  if (!allowed) {
    return <>{props.fallback ?? null}</>;
  }
  return <>{props.children}</>;
}
