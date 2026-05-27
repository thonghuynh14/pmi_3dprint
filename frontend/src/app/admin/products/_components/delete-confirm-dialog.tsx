"use client";

/**
 * Controlled delete confirm dialog. Dùng chung list page + edit page.
 * Caller cung cấp `onConfirm` (hành vi post-delete khác nhau: list ở lại,
 * edit redirect).
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
  /** Tên product đang chờ xoá. null = dialog đóng. */
  productName: string | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  pending?: boolean;
}

export function DeleteConfirmDialog({
  productName,
  onOpenChange,
  onConfirm,
  pending = false,
}: DeleteConfirmDialogProps) {
  return (
    <Dialog open={productName !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xác nhận xoá</DialogTitle>
          <DialogDescription>
            Xoá product &quot;{productName}&quot;? Đây là soft delete — có thể
            khôi phục từ &quot;Show archived&quot;.
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
