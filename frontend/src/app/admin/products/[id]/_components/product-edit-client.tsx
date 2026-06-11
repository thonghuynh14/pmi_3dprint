"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDeleteProduct,
  useProduct,
  useRestoreProduct,
} from "@/lib/hooks/use-products";

import { DeleteConfirmDialog } from "../../_components/delete-confirm-dialog";
import { ProductForm } from "../../_components/product-form";

export function ProductEditClient({ id }: { id: string }) {
  const router = useRouter();
  // includeDeleted: cho phép mở/edit cả product đã archived.
  const { data, isLoading, isError } = useProduct(id, { includeDeleted: true });
  const deleteMutation = useDeleteProduct();
  const restoreMutation = useRestoreProduct();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full max-w-2xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-3 p-6">
        <p className="text-destructive">Không tìm thấy product.</p>
        <Button asChild variant="outline">
          <Link href="/admin/products">← Về danh sách</Link>
        </Button>
      </div>
    );
  }

  function handleDelete() {
    setConfirmingDelete(false);
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success(`Đã xoá "${data!.name}"`, {
          action: {
            label: "Hoàn tác",
            onClick: () => restoreMutation.mutate(id),
          },
        });
        router.push("/admin/products");
      },
    });
  }

  const isDeleted = data.deleted_at !== null;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Link
            href="/admin/products"
            className="text-sm text-muted-foreground hover:underline"
          >
            ← Products
          </Link>
          <h1 className="mt-2 text-2xl font-semibold">{data.name}</h1>
          <p className="font-mono text-xs text-muted-foreground">{data.sku_root}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/admin/products/${id}/variants`}>
              Quản lý variants
            </Link>
          </Button>
          {isDeleted ? (
            <Button
              variant="outline"
              onClick={() => restoreMutation.mutate(id)}
              disabled={restoreMutation.isPending}
            >
              Khôi phục
            </Button>
          ) : (
            <Button
              variant="destructive"
              onClick={() => setConfirmingDelete(true)}
            >
              Xoá
            </Button>
          )}
        </div>
      </div>

      <ProductForm mode="edit" initialData={data} />

      <DeleteConfirmDialog
        productName={confirmingDelete ? data.name : null}
        onOpenChange={(open) => !open && setConfirmingDelete(false)}
        onConfirm={handleDelete}
        pending={deleteMutation.isPending}
      />
    </div>
  );
}
