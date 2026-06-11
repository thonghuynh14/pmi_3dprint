/**
 * API client cho Variant endpoints.
 *
 * - CRUD + restore: mount dưới `/api/v1/skus/variants/`.
 * - Matrix bulk:    `/api/v1/catalog/products/<product_id>/variants/bulk-matrix/`
 *   (nested để giữ ngữ cảnh Product trong URL).
 *
 * apiClient (lib/api/client.ts) đã set baseURL = `${API_BASE_URL}/v1`
 * và gắn JWT Bearer + refresh 401.
 */

import { apiClient } from "./client";

import type {
  VariantInput,
  VariantMatrixInput,
  VariantUpdateInput,
} from "@/lib/schemas/variant";
import type {
  Variant,
  VariantListParams,
  VariantListResponse,
  VariantMatrixResponse,
} from "@/lib/types/variant";

const BASE = "/skus/variants/";

function buildParams(params: VariantListParams): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (params.page !== undefined) out.page = params.page;
  if (params.page_size !== undefined) out.page_size = params.page_size;
  if (params.product) out.product = params.product;
  if (params.search) out.search = params.search;
  if (params.status) out.status = params.status;
  if (params.show_archived) out.show_archived = "true";
  if (params.ordering) out.ordering = params.ordering;
  return out;
}

export async function listVariants(
  params: VariantListParams = {},
): Promise<VariantListResponse> {
  const response = await apiClient.get<VariantListResponse>(BASE, {
    params: buildParams(params),
  });
  return response.data;
}

export async function getVariant(
  id: string,
  options: { includeDeleted?: boolean } = {},
): Promise<Variant> {
  const response = await apiClient.get<Variant>(`${BASE}${id}/`, {
    params: options.includeDeleted ? { show_archived: "true" } : undefined,
  });
  return response.data;
}

export async function createVariant(data: VariantInput): Promise<Variant> {
  const response = await apiClient.post<Variant>(BASE, data);
  return response.data;
}

export async function updateVariant(
  id: string,
  data: VariantUpdateInput,
): Promise<Variant> {
  const response = await apiClient.patch<Variant>(`${BASE}${id}/`, data);
  return response.data;
}

export async function deleteVariant(id: string): Promise<void> {
  await apiClient.delete(`${BASE}${id}/`);
}

export async function restoreVariant(id: string): Promise<Variant> {
  const response = await apiClient.post<Variant>(`${BASE}${id}/restore/`);
  return response.data;
}

/** Matrix bulk creator — nested dưới catalog/products/<id>/. */
export async function createVariantMatrix(
  productId: string,
  data: VariantMatrixInput,
): Promise<VariantMatrixResponse> {
  const response = await apiClient.post<VariantMatrixResponse>(
    `/catalog/products/${productId}/variants/bulk-matrix/`,
    data,
  );
  return response.data;
}
