/**
 * TanStack Query hooks cho Product CRUD.
 *
 * Key factory pattern: cho phép invalidate scope cụ thể (list / detail / all).
 * Mutation tự invalidate cache + toast user-facing message.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { toast } from "sonner";

import {
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  restoreProduct,
  updateProduct,
} from "@/lib/api/products";
import type { ProductInput, ProductUpdateInput } from "@/lib/schemas/product";
import type {
  Product,
  ProductListParams,
  ProductListResponse,
} from "@/lib/types/product";

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------
export const productKeys = {
  all: ["products"] as const,
  lists: () => [...productKeys.all, "list"] as const,
  list: (params: ProductListParams) =>
    [...productKeys.lists(), params] as const,
  details: () => [...productKeys.all, "detail"] as const,
  detail: (id: string) => [...productKeys.details(), id] as const,
};

// ---------------------------------------------------------------------------
// Error extraction
// ---------------------------------------------------------------------------
interface DrfErrorBody {
  detail?: string;
  // Field errors: { sku_root: ["msg"], slug: ["msg"] }
  [field: string]: unknown;
}

function extractErrorMessage(
  error: unknown,
  fallback: string,
): string {
  const axios = error as AxiosError<DrfErrorBody>;
  const body = axios?.response?.data;
  if (!body) return fallback;
  if (typeof body.detail === "string") return body.detail;

  // Field errors → 1st field's 1st message.
  for (const value of Object.values(body)) {
    if (Array.isArray(value) && typeof value[0] === "string") {
      return value[0];
    }
    if (typeof value === "string") {
      return value;
    }
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------
export function useProducts(
  params: ProductListParams = {},
  options?: Pick<
    UseQueryOptions<ProductListResponse>,
    "initialData" | "enabled"
  >,
) {
  return useQuery({
    queryKey: productKeys.list(params),
    queryFn: () => listProducts(params),
    staleTime: 30_000,
    ...options,
  });
}

export function useProduct(
  id: string | null | undefined,
  options?: { includeDeleted?: boolean },
) {
  return useQuery({
    queryKey: productKeys.detail(id ?? ""),
    queryFn: () => getProduct(id!, { includeDeleted: options?.includeDeleted }),
    enabled: !!id,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------
export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProductInput) => createProduct(data),
    onSuccess: (product) => {
      qc.invalidateQueries({ queryKey: productKeys.lists() });
      toast.success(`Đã tạo product "${product.name}"`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không tạo được product."));
    },
  });
}

export function useUpdateProduct(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProductUpdateInput) => updateProduct(id, data),
    onSuccess: (product) => {
      qc.setQueryData<Product>(productKeys.detail(id), product);
      qc.invalidateQueries({ queryKey: productKeys.lists() });
      toast.success(`Đã cập nhật "${product.name}"`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không cập nhật được product."));
    },
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: productKeys.detail(id) });
      qc.invalidateQueries({ queryKey: productKeys.lists() });
      // Toast handled by caller (cần show "Undo" button → defer cho FE
      // component, không gắn cứng ở đây).
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không xoá được product."));
    },
  });
}

export function useRestoreProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => restoreProduct(id),
    onSuccess: (product) => {
      qc.setQueryData<Product>(productKeys.detail(product.id), product);
      qc.invalidateQueries({ queryKey: productKeys.lists() });
      toast.success(`Đã khôi phục "${product.name}"`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không khôi phục được product."));
    },
  });
}
