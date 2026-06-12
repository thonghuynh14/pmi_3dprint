"use client";

import { Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PermissionGuard } from "@/components/auth/permission-guard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useDebounce } from "@/lib/hooks/use-debounce";

const ALL_STATUS = "__all__";

export function VariantsToolbar({ productId }: { productId: string }) {
  const router = useRouter();
  const sp = useSearchParams();

  const [searchInput, setSearchInput] = useState(sp.get("search") ?? "");
  const debouncedSearch = useDebounce(searchInput, 300);

  useEffect(() => {
    const current = sp.get("search") ?? "";
    if (debouncedSearch === current) return;
    const next = new URLSearchParams(sp.toString());
    if (debouncedSearch) next.set("search", debouncedSearch);
    else next.delete("search");
    next.delete("page");
    router.replace(`?${next.toString()}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  function updateParam(key: string, value: string | null) {
    const next = new URLSearchParams(sp.toString());
    if (value === null || value === "") next.delete(key);
    else next.set(key, value);
    next.delete("page");
    router.replace(`?${next.toString()}`);
  }

  const status = sp.get("status") ?? ALL_STATUS;
  const showArchived = sp.get("show_archived") === "true";

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      <div className="flex-1 min-w-[200px] space-y-1">
        <Label htmlFor="search" className="text-xs text-muted-foreground">
          Tìm kiếm
        </Label>
        <Input
          id="search"
          placeholder="SKU hoặc tên..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      <div className="w-40 space-y-1">
        <Label htmlFor="status" className="text-xs text-muted-foreground">
          Status
        </Label>
        <Select
          value={status}
          onValueChange={(v) =>
            updateParam("status", v === ALL_STATUS ? null : v)
          }
        >
          <SelectTrigger id="status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_STATUS}>Tất cả</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2 pb-2">
        <Switch
          id="show_archived"
          checked={showArchived}
          onCheckedChange={(checked) =>
            updateParam("show_archived", checked ? "true" : null)
          }
        />
        <Label htmlFor="show_archived" className="text-sm">
          Show archived
        </Label>
      </div>

      <PermissionGuard perm="variant:create">
        <div className="ml-auto flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/admin/products/${productId}/variants/new-matrix`}>
              <Sparkles className="mr-2 h-4 w-4" />
              Thêm matrix
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/admin/products/${productId}/variants/new`}>
              <Plus className="mr-2 h-4 w-4" />
              Thêm variant
            </Link>
          </Button>
        </div>
      </PermissionGuard>
    </div>
  );
}
