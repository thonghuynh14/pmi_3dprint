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
import type { ProductListItem, ProductStatus } from "@/lib/types/product";

const statusVariant: Record<ProductStatus, "default" | "secondary" | "outline"> = {
  draft: "secondary",
  active: "default",
  archived: "outline",
};

const statusLabel: Record<ProductStatus, string> = {
  draft: "Draft",
  active: "Active",
  archived: "Archived",
};

interface ColumnActions {
  onDelete: (product: ProductListItem) => void;
  onRestore: (product: ProductListItem) => void;
}

export function buildColumns({
  onDelete,
  onRestore,
}: ColumnActions): ColumnDef<ProductListItem>[] {
  return [
    {
      accessorKey: "name",
      header: "Tên",
      cell: ({ row }) => (
        <Link
          href={`/admin/products/${row.original.id}`}
          className="font-medium hover:underline"
        >
          {row.original.name}
        </Link>
      ),
    },
    {
      accessorKey: "sku_root",
      header: "SKU root",
      cell: ({ row }) => (
        <Badge variant="outline" className="font-mono text-xs">
          {row.original.sku_root}
        </Badge>
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
      accessorKey: "brand",
      header: "Brand",
      cell: ({ row }) =>
        row.original.brand || (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      accessorKey: "tags",
      header: "Tags",
      cell: ({ row }) => {
        const tags = row.original.tags;
        if (tags.length === 0)
          return <span className="text-muted-foreground">—</span>;
        const visible = tags.slice(0, 3);
        const rest = tags.length - visible.length;
        return (
          <div className="flex flex-wrap gap-1">
            {visible.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {rest > 0 && (
              <Badge variant="secondary" className="text-xs">
                +{rest}
              </Badge>
            )}
          </div>
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
        const product = row.original;
        const isDeleted = product.deleted_at !== null;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Hành động">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {isDeleted ? (
                <DropdownMenuItem onClick={() => onRestore(product)}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Khôi phục
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  onClick={() => onDelete(product)}
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
