/**
 * API client cho Product endpoints.
 *
 * Mount dưới /api/v1/catalog/products/ (xem backend/config/urls.py).
 * apiClient (lib/api/client.ts) đã set baseURL = ${API_BASE_URL}/v1
 * và gắn JWT Bearer + refresh 401.
 */

import { apiClient } from "./client";

import type {
  Product,
  ProductListParams,
  ProductListResponse,
} from "@/lib/types/product";
import type { ProductInput, ProductUpdateInput } from "@/lib/schemas/product";

const BASE = "/catalog/products/";

function buildParams(params: ProductListParams): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (params.page !== undefined) out.page = params.page;
  if (params.page_size !== undefined) out.page_size = params.page_size;
  if (params.search) out.search = params.search;
  if (params.status) out.status = params.status;
  if (params.show_archived) out.show_archived = "true";
  if (params.ordering) out.ordering = params.ordering;
  return out;
}

export async function listProducts(
  params: ProductListParams = {},
): Promise<ProductListResponse> {
  const response = await apiClient.get<ProductListResponse>(BASE, {
    params: buildParams(params),
  });
  return response.data;
}

export async function getProduct(
  id: string,
  options: { includeDeleted?: boolean } = {},
): Promise<Product> {
  const response = await apiClient.get<Product>(`${BASE}${id}/`, {
    params: options.includeDeleted ? { show_archived: "true" } : undefined,
  });
  return response.data;
}

export async function createProduct(data: ProductInput): Promise<Product> {
  const response = await apiClient.post<Product>(BASE, data);
  return response.data;
}

export async function updateProduct(
  id: string,
  data: ProductUpdateInput,
): Promise<Product> {
  const response = await apiClient.patch<Product>(`${BASE}${id}/`, data);
  return response.data;
}

export async function deleteProduct(id: string): Promise<void> {
  await apiClient.delete(`${BASE}${id}/`);
}

export async function restoreProduct(id: string): Promise<Product> {
  const response = await apiClient.post<Product>(`${BASE}${id}/restore/`);
  return response.data;
}
