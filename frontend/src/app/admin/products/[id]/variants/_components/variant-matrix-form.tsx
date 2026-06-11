"use client";

/**
 * Variant matrix bulk creator form.
 *
 * UI 2 phase:
 * 1. **Input** — user nhập axes (materials/colors/sizes) + price + status.
 *    Realtime hiển thị tổng N×M×P sẽ tạo. Cảnh báo nếu > 50,
 *    disable submit nếu > 100 (BE cap MAX_BATCH).
 * 2. **Preview** — table N×M×P rows (SKU placeholder -XX, name auto-gen).
 *    Button "Quay lại" sửa axes, "Tạo tất cả" gọi BE.
 *
 * Dùng useState cho axes (dynamic arrays — RHF + useFieldArray phức tạp
 * hơn cho dynamic 2-field entries). Validate qua zod schema khi
 * chuyển sang preview.
 */

import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
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
import { useProduct } from "@/lib/hooks/use-products";
import { useCreateVariantMatrix } from "@/lib/hooks/use-variants";
import {
  MAX_VARIANT_BATCH,
  variantMatrixInputSchema,
} from "@/lib/schemas/variant";
import type { AxisEntry, VariantStatus } from "@/lib/types/variant";

import { VariantMatrixPreviewTable } from "./variant-matrix-preview-table";

const CODE3_RE = /^[A-Z0-9]{2,4}$/;
const SIZE_PRESET_RE = /^[A-Za-z0-9]{1,8}$/;
const WARN_THRESHOLD = 50;

// Helper: detect case-insensitive duplicate trong array.
function hasDuplicate(values: string[]): boolean {
  const seen = new Set<string>();
  for (const v of values) {
    const lower = v.toLowerCase();
    if (seen.has(lower)) return true;
    seen.add(lower);
  }
  return false;
}

interface Props {
  productId: string;
}

export function VariantMatrixForm({ productId }: Props) {
  const router = useRouter();
  const productQuery = useProduct(productId);
  const mutation = useCreateVariantMatrix(productId);

  // Axis state
  const [materials, setMaterials] = useState<AxisEntry[]>([]);
  const [colors, setColors] = useState<AxisEntry[]>([]);
  const [sizes, setSizes] = useState<string[]>([]);

  // Temp inputs cho add chip.
  const [tempMatName, setTempMatName] = useState("");
  const [tempMatCode, setTempMatCode] = useState("");
  const [tempColName, setTempColName] = useState("");
  const [tempColCode, setTempColCode] = useState("");
  const [tempSize, setTempSize] = useState("");

  // Pricing + status.
  const [basePrice, setBasePrice] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [status, setStatus] = useState<VariantStatus>("draft");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [phase, setPhase] = useState<"input" | "preview">("input");

  const total = materials.length * colors.length * sizes.length;
  const overLimit = total > MAX_VARIANT_BATCH;
  const warnHigh = total > WARN_THRESHOLD && !overLimit;

  // -------- chip helpers ----------
  function addMaterial() {
    const name = tempMatName.trim();
    const code = tempMatCode.trim().toUpperCase();
    if (!name) {
      setErrors((e) => ({ ...e, _matAdd: "Tên không trống." }));
      return;
    }
    if (!CODE3_RE.test(code)) {
      setErrors((e) => ({ ...e, _matAdd: "code3: 2-4 chữ in hoa/số." }));
      return;
    }
    if (materials.some((m) => m.code3.toLowerCase() === code.toLowerCase())) {
      setErrors((e) => ({ ...e, _matAdd: `code3 "${code}" đã có.` }));
      return;
    }
    setMaterials([...materials, { name, code3: code }]);
    setTempMatName("");
    setTempMatCode("");
    setErrors((e) => ({ ...e, _matAdd: "" }));
  }

  function addColor() {
    const name = tempColName.trim();
    const code = tempColCode.trim().toUpperCase();
    if (!name) {
      setErrors((e) => ({ ...e, _colAdd: "Tên không trống." }));
      return;
    }
    if (!CODE3_RE.test(code)) {
      setErrors((e) => ({ ...e, _colAdd: "code3: 2-4 chữ in hoa/số." }));
      return;
    }
    if (colors.some((c) => c.code3.toLowerCase() === code.toLowerCase())) {
      setErrors((e) => ({ ...e, _colAdd: `code3 "${code}" đã có.` }));
      return;
    }
    setColors([...colors, { name, code3: code }]);
    setTempColName("");
    setTempColCode("");
    setErrors((e) => ({ ...e, _colAdd: "" }));
  }

  function addSize() {
    const s = tempSize.trim();
    if (!s) return;
    if (!SIZE_PRESET_RE.test(s)) {
      setErrors((e) => ({ ...e, _sizeAdd: "1-8 ký tự alphanumeric." }));
      return;
    }
    if (sizes.some((existing) => existing.toLowerCase() === s.toLowerCase())) {
      setErrors((e) => ({ ...e, _sizeAdd: `"${s}" đã có.` }));
      return;
    }
    setSizes([...sizes, s]);
    setTempSize("");
    setErrors((e) => ({ ...e, _sizeAdd: "" }));
  }

  function removeMaterial(i: number) {
    setMaterials(materials.filter((_, idx) => idx !== i));
  }

  function removeColor(i: number) {
    setColors(colors.filter((_, idx) => idx !== i));
  }

  function removeSize(i: number) {
    setSizes(sizes.filter((_, idx) => idx !== i));
  }

  // -------- preview / submit ----------
  function handlePreview() {
    const newErrors: Record<string, string> = {};
    if (materials.length === 0) newErrors.materials = "Cần ≥ 1 material.";
    if (colors.length === 0) newErrors.colors = "Cần ≥ 1 color.";
    if (sizes.length === 0) newErrors.sizes = "Cần ≥ 1 size.";
    if (
      hasDuplicate(materials.map((m) => m.code3)) ||
      hasDuplicate(colors.map((c) => c.code3)) ||
      hasDuplicate(sizes)
    ) {
      newErrors._dup = "Có giá trị axis trùng (case-insensitive).";
    }
    if (overLimit) {
      newErrors._batch = `Tổng ${total} > ${MAX_VARIANT_BATCH} — vượt giới hạn.`;
    }
    // Pricing validate qua schema dưới.

    const parsed = variantMatrixInputSchema.safeParse({
      materials,
      colors,
      sizes,
      base_price: basePrice,
      cost_price: costPrice === "" ? null : costPrice,
      status,
    });
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        const key = issue.path.join(".") || "_form";
        if (!newErrors[key]) newErrors[key] = issue.message;
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    if (warnHigh) {
      // Confirm modal đơn giản qua confirm() native — đủ cho v1.
      const ok = window.confirm(
        `Bạn sắp tạo ${total} variants. Tiếp tục?`,
      );
      if (!ok) return;
    }
    setPhase("preview");
  }

  function handleSubmit() {
    const parsed = variantMatrixInputSchema.safeParse({
      materials,
      colors,
      sizes,
      base_price: basePrice,
      cost_price: costPrice === "" ? null : costPrice,
      status,
    });
    if (!parsed.success) {
      // Re-validate (đã làm ở preview, defensive)
      setPhase("input");
      return;
    }
    mutation.mutate(parsed.data, {
      onSuccess: () => {
        router.push(`/admin/products/${productId}/variants`);
      },
      onError: (error) => {
        // Đã có toast tại hook; thêm fallback đưa user về input mode.
        setPhase("input");
        void error;
        toast.error("Tạo matrix thất bại — sửa và thử lại.");
      },
    });
  }

  const product = productQuery.data;

  // -------- render ----------
  if (phase === "preview") {
    if (!product) return null;
    return (
      <div className="max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">
              Sẽ tạo {total} variants
            </h2>
            <p className="text-sm text-muted-foreground">
              base_price = {basePrice}đ, status = {status}.{" "}
              {warnHigh && (
                <span className="text-amber-600">
                  ⚠️ Số lượng lớn ({total}).
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setPhase("input")}
              disabled={mutation.isPending}
            >
              ← Quay lại sửa axes
            </Button>
            <Button onClick={handleSubmit} disabled={mutation.isPending}>
              {mutation.isPending
                ? "Đang tạo..."
                : `Tạo ${total} variants`}
            </Button>
          </div>
        </div>

        <VariantMatrixPreviewTable
          productSkuRoot={product.sku_root}
          productName={product.name}
          materials={materials}
          colors={colors}
          sizes={sizes}
        />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-8">
      {/* Materials */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-medium">Materials</h2>
          <p className="text-xs text-muted-foreground">
            Nhập tên + code 3 (vd PLA, PETG). code3 đi vào SKU.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {materials.map((m, i) => (
            <Badge
              key={`${m.code3}-${i}`}
              variant="secondary"
              className="gap-2 py-1.5 pl-3 pr-1"
            >
              <span className="text-xs">
                {m.name}{" "}
                <span className="font-mono text-muted-foreground">
                  ({m.code3})
                </span>
              </span>
              <button
                type="button"
                onClick={() => removeMaterial(i)}
                className="rounded-full p-0.5 hover:bg-background"
                aria-label={`Xoá ${m.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {materials.length === 0 && (
            <span className="text-xs text-muted-foreground">
              Chưa có material nào.
            </span>
          )}
        </div>
        <div className="grid grid-cols-[1fr_140px_auto] gap-2">
          <Input
            placeholder="Tên (Polylactic Acid)"
            value={tempMatName}
            onChange={(e) => setTempMatName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addMaterial();
              }
            }}
          />
          <Input
            placeholder="Code (PLA)"
            value={tempMatCode}
            onChange={(e) => setTempMatCode(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addMaterial();
              }
            }}
            className="font-mono"
            maxLength={4}
          />
          <Button type="button" variant="outline" onClick={addMaterial}>
            Thêm
          </Button>
        </div>
        {(errors._matAdd || errors.materials) && (
          <p className="text-xs text-destructive">
            {errors._matAdd || errors.materials}
          </p>
        )}
      </section>

      {/* Colors */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-medium">Colors</h2>
          <p className="text-xs text-muted-foreground">
            Tên + code 3 (vd RED, BLU, GRN).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {colors.map((c, i) => (
            <Badge
              key={`${c.code3}-${i}`}
              variant="secondary"
              className="gap-2 py-1.5 pl-3 pr-1"
            >
              <span className="text-xs">
                {c.name}{" "}
                <span className="font-mono text-muted-foreground">
                  ({c.code3})
                </span>
              </span>
              <button
                type="button"
                onClick={() => removeColor(i)}
                className="rounded-full p-0.5 hover:bg-background"
                aria-label={`Xoá ${c.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {colors.length === 0 && (
            <span className="text-xs text-muted-foreground">
              Chưa có color nào.
            </span>
          )}
        </div>
        <div className="grid grid-cols-[1fr_140px_auto] gap-2">
          <Input
            placeholder="Tên (Red)"
            value={tempColName}
            onChange={(e) => setTempColName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addColor();
              }
            }}
          />
          <Input
            placeholder="Code (RED)"
            value={tempColCode}
            onChange={(e) => setTempColCode(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addColor();
              }
            }}
            className="font-mono"
            maxLength={4}
          />
          <Button type="button" variant="outline" onClick={addColor}>
            Thêm
          </Button>
        </div>
        {(errors._colAdd || errors.colors) && (
          <p className="text-xs text-destructive">
            {errors._colAdd || errors.colors}
          </p>
        )}
      </section>

      {/* Sizes */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-medium">Sizes</h2>
          <p className="text-xs text-muted-foreground">
            Vd S / M / L / XL / 12cm. 1-8 ký tự alphanumeric.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {sizes.map((s, i) => (
            <Badge
              key={`${s}-${i}`}
              variant="secondary"
              className="gap-2 py-1.5 pl-3 pr-1"
            >
              <span className="font-mono text-xs">{s}</span>
              <button
                type="button"
                onClick={() => removeSize(i)}
                className="rounded-full p-0.5 hover:bg-background"
                aria-label={`Xoá ${s}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {sizes.length === 0 && (
            <span className="text-xs text-muted-foreground">
              Chưa có size nào.
            </span>
          )}
        </div>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <Input
            placeholder="Vd M, L, XL hoặc 12cm"
            value={tempSize}
            onChange={(e) => setTempSize(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addSize();
              }
            }}
            maxLength={8}
          />
          <Button type="button" variant="outline" onClick={addSize}>
            Thêm
          </Button>
        </div>
        {(errors._sizeAdd || errors.sizes) && (
          <p className="text-xs text-destructive">
            {errors._sizeAdd || errors.sizes}
          </p>
        )}
      </section>

      {/* Pricing */}
      <section className="space-y-4 border-t pt-6">
        <h2 className="text-sm font-medium">Pricing chung (áp cho cả batch)</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label htmlFor="base_price">Giá bán (VND) *</Label>
            <Input
              id="base_price"
              type="number"
              step="1000"
              min="0"
              placeholder="150000"
              value={basePrice}
              onChange={(e) => setBasePrice(e.target.value)}
            />
            {errors.base_price && (
              <p className="text-xs text-destructive">{errors.base_price}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="cost_price">Cost (VND)</Label>
            <Input
              id="cost_price"
              type="number"
              step="1000"
              min="0"
              placeholder="(tuỳ chọn)"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
            />
            {errors.cost_price && (
              <p className="text-xs text-destructive">{errors.cost_price}</p>
            )}
          </div>
        </div>

        <div className="space-y-1 max-w-[200px]">
          <Label htmlFor="status">Status</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as VariantStatus)}>
            <SelectTrigger id="status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      {/* Submit */}
      <section className="space-y-3 border-t pt-6">
        {errors._dup && (
          <p className="text-sm text-destructive">{errors._dup}</p>
        )}
        {errors._batch && (
          <p className="text-sm text-destructive">{errors._batch}</p>
        )}
        <div className="flex items-center justify-between">
          <p className="text-sm">
            Sẽ tạo{" "}
            <strong
              className={
                overLimit
                  ? "text-destructive"
                  : warnHigh
                    ? "text-amber-600"
                    : ""
              }
            >
              {total}
            </strong>{" "}
            variants
            {warnHigh && (
              <span className="ml-2 text-xs text-amber-600">
                (cảnh báo: &gt; {WARN_THRESHOLD})
              </span>
            )}
            {overLimit && (
              <span className="ml-2 text-xs text-destructive">
                (vượt giới hạn {MAX_VARIANT_BATCH})
              </span>
            )}
          </p>
          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                router.push(`/admin/products/${productId}/variants`)
              }
            >
              Huỷ
            </Button>
            <Button
              type="button"
              onClick={handlePreview}
              disabled={total === 0 || overLimit}
            >
              Preview {total > 0 && `(${total})`}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
