/**
 * TanStack Query hooks cho Variant CRUD + matrix bulk.
 *
 * Pattern y hệt use-products: queryKey factory + invalidate per mutation
 * + toast message. extractErrorMessage có thêm nhánh xử lý detail dict
 * (BE Variant exceptions như BatchTooLarge / FieldImmutable trả detail
 * dạng object có key "detail" bên trong).
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
  createVariant,
  createVariantMatrix,
  deleteVariant,
  getVariant,
  listVariants,
  restoreVariant,
  updateVariant,
} from "@/lib/api/variants";
import type {
  VariantInput,
  VariantMatrixInput,
  VariantUpdateInput,
} from "@/lib/schemas/variant";
import type {
  Variant,
  VariantListParams,
  VariantListResponse,
} from "@/lib/types/variant";

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------
export const variantKeys = {
  all: ["variants"] as const,
  lists: () => [...variantKeys.all, "list"] as const,
  list: (params: VariantListParams) =>
    [...variantKeys.lists(), params] as const,
  details: () => [...variantKeys.all, "detail"] as const,
  detail: (id: string) => [...variantKeys.details(), id] as const,
};

// ---------------------------------------------------------------------------
// Error extraction
// ---------------------------------------------------------------------------
interface DrfErrorBody {
  detail?: string | { detail?: string; [key: string]: unknown };
  [field: string]: unknown;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  const axios = error as AxiosError<DrfErrorBody>;
  const body = axios?.response?.data;
  if (!body) return fallback;

  // BatchTooLarge / FieldImmutable / SkuLengthInvalid trả detail dạng dict
  // {"detail": "msg", "field": "...", ...} → đọc detail.detail.
  if (
    typeof body.detail === "object" &&
    body.detail !== null &&
    "detail" in body.detail &&
    typeof body.detail.detail === "string"
  ) {
    return body.detail.detail;
  }
  if (typeof body.detail === "string") return body.detail;

  // Field-level errors: {"sku_root": ["msg"], ...}
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
export function useVariants(
  params: VariantListParams = {},
  options?: Pick<
    UseQueryOptions<VariantListResponse>,
    "initialData" | "enabled"
  >,
) {
  return useQuery({
    queryKey: variantKeys.list(params),
    queryFn: () => listVariants(params),
    staleTime: 30_000,
    ...options,
  });
}

export function useVariant(
  id: string | null | undefined,
  options?: { includeDeleted?: boolean },
) {
  return useQuery({
    queryKey: variantKeys.detail(id ?? ""),
    queryFn: () =>
      getVariant(id!, { includeDeleted: options?.includeDeleted }),
    enabled: !!id,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------
export function useCreateVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VariantInput) => createVariant(data),
    onSuccess: (variant) => {
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      toast.success(`Đã tạo variant ${variant.sku}`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không tạo được variant."));
    },
  });
}

export function useUpdateVariant(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VariantUpdateInput) => updateVariant(id, data),
    onSuccess: (variant) => {
      qc.setQueryData<Variant>(variantKeys.detail(id), variant);
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      toast.success(`Đã cập nhật ${variant.sku}`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không cập nhật được variant."));
    },
  });
}

export function useDeleteVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteVariant(id),
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: variantKeys.detail(id) });
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      // Toast handled by caller (cho phép show "Undo" button).
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không xoá được variant."));
    },
  });
}

export function useRestoreVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => restoreVariant(id),
    onSuccess: (variant) => {
      qc.setQueryData<Variant>(variantKeys.detail(variant.id), variant);
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      toast.success(`Đã khôi phục ${variant.sku}`);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không khôi phục được variant."));
    },
  });
}

/** Matrix bulk creator. ProductId vào hook (constant cho cả mutation lifetime),
 * payload (materials/colors/sizes/price/status) vào mutate(). */
export function useCreateVariantMatrix(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VariantMatrixInput) =>
      createVariantMatrix(productId, data),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      toast.success(`Đã tạo ${result.count} variants`);
    },
    onError: (error) => {
      toast.error(
        extractErrorMessage(error, "Không tạo được matrix variants."),
      );
    },
  });
}
