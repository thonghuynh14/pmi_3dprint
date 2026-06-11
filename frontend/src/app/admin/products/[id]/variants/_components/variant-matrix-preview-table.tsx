"use client";

/**
 * Preview N×M×P combos trước khi submit matrix.
 *
 * SKU hiển thị placeholder ``-XX`` cho ``sequence_no`` (NN) — BE assign
 * thật khi tạo (atomic, select_for_update Product). FE không tính được
 * sequence_no thật từ trước (không biết max hiện tại trên product).
 */

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AxisEntry } from "@/lib/types/variant";

interface Props {
  productSkuRoot: string;
  productName: string;
  materials: AxisEntry[];
  colors: AxisEntry[];
  sizes: string[];
}

export function VariantMatrixPreviewTable({
  productSkuRoot,
  productName,
  materials,
  colors,
  sizes,
}: Props) {
  const rows: {
    skuPreview: string;
    name: string;
    material: AxisEntry;
    color: AxisEntry;
    size: string;
  }[] = [];

  for (const m of materials) {
    for (const c of colors) {
      for (const s of sizes) {
        rows.push({
          skuPreview: `${productSkuRoot}-${m.code3}-${c.code3}-${s}-XX`,
          name: `${productName} - ${m.name} ${c.name} ${s}`,
          material: m,
          color: c,
          size: s,
        });
      }
    }
  }

  return (
    <div className="rounded-md border bg-background">
      <div className="border-b bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
        SKU sẽ hiển thị <code className="font-mono">-XX</code> ở phần
        sequence_no — BE assign số thật khi tạo.
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10 text-center">#</TableHead>
            <TableHead>SKU preview</TableHead>
            <TableHead>Material</TableHead>
            <TableHead>Color</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Name (auto-gen)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            <TableRow key={`${r.material.code3}-${r.color.code3}-${r.size}`}>
              <TableCell className="text-center text-xs text-muted-foreground">
                {i + 1}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {r.skuPreview}
              </TableCell>
              <TableCell>
                <span className="text-sm">{r.material.name}</span>{" "}
                <Badge variant="outline" className="font-mono text-xs">
                  {r.material.code3}
                </Badge>
              </TableCell>
              <TableCell>
                <span className="text-sm">{r.color.name}</span>{" "}
                <Badge variant="outline" className="font-mono text-xs">
                  {r.color.code3}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="font-mono text-xs">
                  {r.size}
                </Badge>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {r.name}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
