/**
 * TS types mirror BE serializer ở apps/accounts/serializers/auth.py.
 */

export type RoleCode =
  | "super_admin"
  | "catalog_manager"
  | "production_manager"
  | "channel_operator"
  | "designer"
  | "cashier";

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: RoleCode | null;
  is_active: boolean;
}

/** Response của POST /auth/login/. */
export interface LoginResponse {
  user: AuthUser;
}

/** Response của GET /auth/me/. */
export interface MeResponse {
  user: AuthUser;
  permissions: string[];
}

/** Permission code format `domain:action`. */
export type PermissionCode = string;
