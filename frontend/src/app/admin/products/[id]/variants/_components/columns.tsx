"use client";

import { type ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { vi } from "date-fns/locale";
import { MoreHorizontal, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { VariantListItem, VariantStatus } from "@/lib/types/variant";

const statusVariant: Record<VariantStatus, "default" | "secondary" | "outline"> = {
  draft: "secondary",
  active: "default",
  archived: "outline",
};

const statusLabel: Record<VariantStatus, string> = {
  draft: "Draft",
  active: "Active",
  archived: "Archived",
};

interface ColumnActions {
  productId: string;
  onDelete: (variant: VariantListItem) => void;
  onRestore: (variant: VariantListItem) => void;
}

const priceFmt = new Intl.NumberFormat("vi-VN");

export function buildColumns({
  productId,
  onDelete,
  onRestore,
}: ColumnActions): ColumnDef<VariantListItem>[] {
  return [
    {
      accessorKey: "sku",
      header: "SKU",
      cell: ({ row }) => (
        <Link
          href={`/admin/products/${productId}/variants/${row.original.id}`}
          className="font-mono text-xs hover:underline"
        >
          {row.original.sku}
        </Link>
      ),
    },
    {
      accessorKey: "name",
      header: "Tên",
      cell: ({ row }) => (
        <span className="text-sm">{row.original.name}</span>
      ),
    },
    {
      id: "axes",
      header: "Axes",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          <Badge variant="outline" className="font-mono text-xs">
            {row.original.material_code3}
          </Badge>
          <Badge variant="outline" className="font-mono text-xs">
            {row.original.color_code3}
          </Badge>
          <Badge variant="outline" className="font-mono text-xs">
            {row.original.size_preset}
          </Badge>
        </div>
      ),
    },
    {
      accessorKey: "base_price",
      header: "Giá bán",
      cell: ({ row }) => (
        <span className="font-mono text-xs">
          {priceFmt.format(Number(row.original.base_price))}đ
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const isDeleted = row.original.deleted_at !== null;
        if (isDeleted) {
          return (
            <Badge variant="destructive" className="text-xs">
              Đã xoá
            </Badge>
          );
        }
        const status = row.original.status;
        return (
          <Badge variant={statusVariant[status]} className="text-xs">
            {statusLabel[status]}
          </Badge>
        );
      },
    },
    {
      accessorKey: "updated_at",
      header: "Cập nhật",
      cell: ({ row }) => (
        <span
          className="text-xs text-muted-foreground"
          title={row.original.updated_at}
        >
          {formatDistanceToNow(new Date(row.original.updated_at), {
            addSuffix: true,
            locale: vi,
          })}
        </span>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => {
        const variant = row.original;
        const isDeleted = variant.deleted_at !== null;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Hành động">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {isDeleted ? (
                <DropdownMenuItem onClick={() => onRestore(variant)}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Khôi phục
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  onClick={() => onDelete(variant)}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Xoá
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];
}
