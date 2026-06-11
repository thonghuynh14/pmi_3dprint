"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useProduct } from "@/lib/hooks/use-products";
import {
  useDeleteVariant,
  useRestoreVariant,
  useVariants,
} from "@/lib/hooks/use-variants";
import type {
  VariantListItem,
  VariantListParams,
  VariantStatus,
} from "@/lib/types/variant";

import { buildColumns } from "./columns";
import { DeleteConfirmDialog } from "./delete-confirm-dialog";
import { VariantsToolbar } from "./variants-toolbar";

const PAGE_SIZE = 20;

function parseParams(
  sp: URLSearchParams,
  productId: string,
): VariantListParams {
  const status = sp.get("status");
  return {
    page: Number(sp.get("page") ?? 1),
    page_size: PAGE_SIZE,
    product: productId,
    search: sp.get("search") ?? "",
    status:
      status && ["draft", "active", "archived"].includes(status)
        ? (status as VariantStatus)
        : undefined,
    show_archived: sp.get("show_archived") === "true",
  };
}

export function VariantsListClient({ productId }: { productId: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  const params = useMemo(() => parseParams(sp, productId), [sp, productId]);

  const productQuery = useProduct(productId);
  const { data, isLoading, isError, error, refetch } = useVariants(params);
  const deleteMutation = useDeleteVariant();
  const restoreMutation = useRestoreVariant();

  const [pendingDelete, setPendingDelete] = useState<VariantListItem | null>(
    null,
  );

  const columns = useMemo(
    () =>
      buildColumns({
        productId,
        onDelete: setPendingDelete,
        onRestore: (variant) => restoreMutation.mutate(variant.id),
      }),
    [productId, restoreMutation],
  );

  const table = useReactTable({
    data: data?.results ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = data
    ? Math.max(1, Math.ceil(data.count / PAGE_SIZE))
    : 1;
  const currentPage = params.page ?? 1;

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    const next = new URLSearchParams(sp.toString());
    next.set("page", String(page));
    router.replace(`?${next.toString()}`);
  }

  function confirmDelete() {
    if (!pendingDelete) return;
    const variant = pendingDelete;
    setPendingDelete(null);
    deleteMutation.mutate(variant.id, {
      onSuccess: () => {
        toast.success(`Đã xoá ${variant.sku}`, {
          action: {
            label: "Hoàn tác",
            onClick: () => restoreMutation.mutate(variant.id),
          },
        });
      },
    });
  }

  const product = productQuery.data;

  return (
    <div className="space-y-4">
      {/* Breadcrumb + header */}
      <div className="mb-2">
        <Link
          href="/admin/products"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Products
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">
          Variants
          {product && (
            <span className="ml-2 text-base font-normal text-muted-foreground">
              của {product.name}{" "}
              <span className="font-mono text-xs">({product.sku_root})</span>
            </span>
          )}
        </h1>
      </div>

      <VariantsToolbar productId={productId} />

      <div className="rounded-md border bg-background">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={`skel-${i}`}>
                  {columns.map((_col, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : isError ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  <div className="space-y-2">
                    <p className="text-sm text-destructive">
                      Lỗi tải dữ liệu:{" "}
                      {(error as Error)?.message ?? "Unknown"}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => refetch()}
                    >
                      Thử lại
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center"
                >
                  <div className="space-y-2 text-muted-foreground">
                    <p>Chưa có variant nào.</p>
                    <Button asChild variant="link">
                      <Link
                        href={`/admin/products/${productId}/variants/new-matrix`}
                      >
                        Tạo matrix variants đầu tiên
                      </Link>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.count > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Trang {currentPage} / {totalPages} · {data.count} variants
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
            >
              Trước
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              Sau
            </Button>
          </div>
        </div>
      )}

      <DeleteConfirmDialog
        variantSku={pendingDelete?.sku ?? null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        onConfirm={confirmDelete}
        pending={deleteMutation.isPending}
      />
    </div>
  );
}
