/**
 * TS types mirror Django `ProductOutputSerializer` (xem
 * backend/apps/catalog/serializers/products.py).
 *
 * Single source of truth: BE serializer. Khi BE đổi field → update ở đây.
 * Khi BE có drf-spectacular OpenAPI schema ổn định, generate type qua
 * openapi-typescript thay vì viết tay.
 */

export type ProductStatus = "draft" | "active" | "archived";

/** Nested user info từ BE _UserSlimSerializer. */
export interface UserSlim {
  id: number;
  username: string;
}

/** Full Product object — output từ retrieve / create / update / restore. */
export interface Product {
  id: string;
  name: string;
  slug: string;
  sku_root: string;
  status: ProductStatus;
  short_description: string;
  long_description: string;
  brand: string;
  tags: string[];
  attributes: Record<string, unknown>;
  created_at: string;  // ISO 8601 với timezone
  updated_at: string;
  deleted_at: string | null;
  created_by: UserSlim | null;
  updated_by: UserSlim | null;
  deleted_by: UserSlim | null;
}

/** Hẹp hơn Product — output cho list endpoint (ProductListItemSerializer).
 * Không có long_description, attributes (heavy), không nested user. */
export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  sku_root: string;
  status: ProductStatus;
  brand: string;
  tags: string[];
  updated_at: string;
  deleted_at: string | null;
}

/** DRF PageNumberPagination response shape. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ProductListResponse = PaginatedResponse<ProductListItem>;

/** Query params cho list endpoint. */
export interface ProductListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: ProductStatus;
  show_archived?: boolean;
  ordering?: string;
}
