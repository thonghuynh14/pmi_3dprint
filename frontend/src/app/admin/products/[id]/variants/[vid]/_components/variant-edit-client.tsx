"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useVariant } from "@/lib/hooks/use-variants";

import { VariantForm } from "../../_components/variant-form";

interface Props {
  productId: string;
  variantId: string;
}

export function VariantEditClient({ productId, variantId }: Props) {
  const { data: variant, isLoading, isError, error } = useVariant(variantId, {
    includeDeleted: true,
  });

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/admin/products/${productId}/variants`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Variants
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">
          Sửa variant{" "}
          {variant && (
            <span className="font-mono text-base text-muted-foreground">
              {variant.sku}
            </span>
          )}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Chỉ sửa được giá bán, cost, status. Axes là immutable (đổi axes =
          đổi SKU = tạo variant mới).
        </p>
      </div>

      {isLoading && (
        <div className="max-w-2xl space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-destructive">
          Lỗi tải variant: {(error as Error)?.message ?? "Unknown"}
        </p>
      )}

      {variant && (
        <VariantForm
          mode="edit"
          productId={productId}
          initialData={variant}
        />
      )}
    </div>
  );
}
