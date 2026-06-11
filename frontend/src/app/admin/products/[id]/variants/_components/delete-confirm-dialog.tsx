"use client";

/**
 * Variant delete confirm dialog. SKU dùng làm identifier (unique, ngắn,
 * dễ nhớ hơn UUID hay tên dài).
 */

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface DeleteConfirmDialogProps {
  /** SKU đang chờ xoá. null = dialog đóng. */
  variantSku: string | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  pending?: boolean;
}

export function DeleteConfirmDialog({
  variantSku,
  onOpenChange,
  onConfirm,
  pending = false,
}: DeleteConfirmDialogProps) {
  return (
    <Dialog open={variantSku !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xác nhận xoá</DialogTitle>
          <DialogDescription>
            Xoá variant <span className="font-mono">{variantSku}</span>? Đây là
            soft delete — có thể khôi phục từ &quot;Show archived&quot;.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Huỷ
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={pending}>
            {pending ? "Đang xoá..." : "Xoá"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
