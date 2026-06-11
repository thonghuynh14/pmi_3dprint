/**
 * TS types mirror Django `VariantOutputSerializer` + `VariantListItemSerializer`
 * (xem backend/apps/skus/serializers/variants.py).
 *
 * Single source of truth: BE serializer. Khi BE đổi field → update ở đây.
 */

export type VariantStatus = "draft" | "active" | "archived";

/** Nested user info từ BE _UserSlimSerializer. */
export interface UserSlim {
  id: number;
  username: string;
}

/** Full Variant — output từ retrieve / create / update / restore. */
export interface Variant {
  id: string;
  sku: string;
  sequence_no: number;
  name: string;
  product_id: string;
  product_name: string;
  material_name: string;
  material_code3: string;
  color_name: string;
  color_code3: string;
  size_preset: string;
  /** DRF DecimalField serialize ra string ("150000.00"). */
  base_price: string;
  cost_price: string | null;
  status: VariantStatus;
  attributes: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  created_by: UserSlim | null;
  updated_by: UserSlim | null;
  deleted_by: UserSlim | null;
}

/** Hẹp hơn — list endpoint (VariantListItemSerializer). */
export interface VariantListItem {
  id: string;
  sku: string;
  name: string;
  sequence_no: number;
  material_code3: string;
  color_code3: string;
  size_preset: string;
  base_price: string;
  status: VariantStatus;
  updated_at: string;
  deleted_at: string | null;
}

/** DRF PageNumberPagination shape. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type VariantListResponse = PaginatedResponse<VariantListItem>;

/** Query params cho list endpoint. */
export interface VariantListParams {
  page?: number;
  page_size?: number;
  /** Filter theo product UUID (optional — không truyền = mọi product). */
  product?: string;
  search?: string;
  status?: VariantStatus;
  show_archived?: boolean;
  ordering?: string;
}

/** Response của matrix bulk endpoint
 * (POST /catalog/products/<id>/variants/bulk-matrix/). */
export interface VariantMatrixResponse {
  count: number;
  created: Variant[];
}

/** 1 entry trong matrix axis input. */
export interface AxisEntry {
  name: string;
  code3: string;
}
