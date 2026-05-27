"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
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
import {
  useDeleteProduct,
  useProducts,
  useRestoreProduct,
} from "@/lib/hooks/use-products";
import type {
  ProductListItem,
  ProductListParams,
  ProductStatus,
} from "@/lib/types/product";

import { buildColumns } from "./columns";
import { DeleteConfirmDialog } from "./delete-confirm-dialog";
import { ProductsToolbar } from "./products-toolbar";

const PAGE_SIZE = 20;

function parseParams(sp: URLSearchParams): ProductListParams {
  const status = sp.get("status");
  return {
    page: Number(sp.get("page") ?? 1),
    page_size: PAGE_SIZE,
    search: sp.get("search") ?? "",
    status: status && ["draft", "active", "archived"].includes(status)
      ? (status as ProductStatus)
      : undefined,
    show_archived: sp.get("show_archived") === "true",
  };
}

export function ProductsListClient() {
  const router = useRouter();
  const sp = useSearchParams();
  const params = useMemo(() => parseParams(sp), [sp]);

  const { data, isLoading, isError, error, refetch } = useProducts(params);
  const deleteMutation = useDeleteProduct();
  const restoreMutation = useRestoreProduct();

  const [pendingDelete, setPendingDelete] = useState<ProductListItem | null>(null);

  const columns = useMemo(
    () =>
      buildColumns({
        onDelete: setPendingDelete,
        onRestore: (product) => {
          restoreMutation.mutate(product.id);
        },
      }),
    [restoreMutation],
  );

  const table = useReactTable({
    data: data?.results ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const currentPage = params.page ?? 1;

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    const next = new URLSearchParams(sp.toString());
    next.set("page", String(page));
    router.replace(`?${next.toString()}`);
  }

  function confirmDelete() {
    if (!pendingDelete) return;
    const product = pendingDelete;
    setPendingDelete(null);
    deleteMutation.mutate(product.id, {
      onSuccess: () => {
        toast.success(`Đã xoá "${product.name}"`, {
          action: {
            label: "Hoàn tác",
            onClick: () => restoreMutation.mutate(product.id),
          },
        });
      },
    });
  }

  return (
    <div className="space-y-4">
      <ProductsToolbar />

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
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  <div className="space-y-2">
                    <p className="text-sm text-destructive">
                      Lỗi tải dữ liệu: {(error as Error)?.message ?? "Unknown"}
                    </p>
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      Thử lại
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 text-center">
                  <div className="space-y-2 text-muted-foreground">
                    <p>Chưa có product nào.</p>
                    <Button asChild variant="link">
                      <a href="/admin/products/new">Tạo product đầu tiên</a>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
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
            Trang {currentPage} / {totalPages} · {data.count} products
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
        productName={pendingDelete?.name ?? null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        onConfirm={confirmDelete}
        pending={deleteMutation.isPending}
      />
    </div>
  );
}
