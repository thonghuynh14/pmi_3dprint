"use client";

/**
 * Variant form — shared create + edit.
 *
 * Create mode: tất cả field editable.
 * Edit mode: axis fields (material/color/size/sku) readonly; chỉ
 * base_price/cost_price/status editable (match BE VariantUpdateSerializer).
 *
 * BE field errors (400) map ngược vào RHF setError để hiển thị inline.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import type { AxiosError } from "axios";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateVariant,
  useUpdateVariant,
} from "@/lib/hooks/use-variants";
import type {
  VariantInput,
  VariantUpdateInput,
} from "@/lib/schemas/variant";
import type { Variant } from "@/lib/types/variant";

const CODE3_RE = /^[A-Z0-9]{2,4}$/;
const SIZE_PRESET_RE = /^[A-Za-z0-9]{1,8}$/;

function isValidPriceString(s: string): boolean {
  if (s === "") return false;
  const n = Number(s);
  return Number.isFinite(n) && n >= 0;
}

function isValidOptionalPriceString(s: string): boolean {
  if (s === "") return true;
  return isValidPriceString(s);
}

const formSchema = z.object({
  material_name: z
    .string()
    .min(1, "Tên material không trống.")
    .max(64, "Tối đa 64 ký tự."),
  material_code3: z
    .string()
    .min(2, "Tối thiểu 2 ký tự.")
    .max(4, "Tối đa 4 ký tự.")
    .refine((v) => CODE3_RE.test(v.toUpperCase()), "Chỉ chữ và số (A-Z, 0-9)."),
  color_name: z
    .string()
    .min(1, "Tên color không trống.")
    .max(64, "Tối đa 64 ký tự."),
  color_code3: z
    .string()
    .min(2, "Tối thiểu 2 ký tự.")
    .max(4, "Tối đa 4 ký tự.")
    .refine((v) => CODE3_RE.test(v.toUpperCase()), "Chỉ chữ và số (A-Z, 0-9)."),
  size_preset: z
    .string()
    .min(1, "Không trống.")
    .max(8, "Tối đa 8 ký tự.")
    .refine((v) => SIZE_PRESET_RE.test(v), "Alphanumeric 1-8 ký tự."),
  base_price: z
    .string()
    .refine(isValidPriceString, "Giá ≥ 0."),
  cost_price: z
    .string()
    .refine(isValidOptionalPriceString, "Cost ≥ 0 (hoặc để trống)."),
  status: z.enum(["draft", "active", "archived"]),
});

type FormValues = z.infer<typeof formSchema>;

// BE field name → form field name (1:1 ở variant).
const BE_TO_FORM_FIELD: Record<string, keyof FormValues> = {
  material_name: "material_name",
  material_code3: "material_code3",
  color_name: "color_name",
  color_code3: "color_code3",
  size_preset: "size_preset",
  base_price: "base_price",
  cost_price: "cost_price",
  status: "status",
};

function toFormValues(variant?: Variant): FormValues {
  return {
    material_name: variant?.material_name ?? "",
    material_code3: variant?.material_code3 ?? "",
    color_name: variant?.color_name ?? "",
    color_code3: variant?.color_code3 ?? "",
    size_preset: variant?.size_preset ?? "",
    base_price: variant?.base_price ?? "",
    cost_price: variant?.cost_price ?? "",
    status: variant?.status ?? "draft",
  };
}

function toCreatePayload(
  values: FormValues,
  productId: string,
): VariantInput {
  return {
    product_id: productId,
    material_name: values.material_name,
    material_code3: values.material_code3.toUpperCase(),
    color_name: values.color_name,
    color_code3: values.color_code3.toUpperCase(),
    size_preset: values.size_preset,
    base_price: Number(values.base_price),
    cost_price:
      values.cost_price === "" ? null : Number(values.cost_price),
    status: values.status,
    attributes: {},
  };
}

function toUpdatePayload(
  values: FormValues,
  dirtyFields: Partial<Record<keyof FormValues, boolean>>,
): VariantUpdateInput {
  const payload: VariantUpdateInput = {};
  if (dirtyFields.base_price) payload.base_price = Number(values.base_price);
  if (dirtyFields.cost_price)
    payload.cost_price =
      values.cost_price === "" ? null : Number(values.cost_price);
  if (dirtyFields.status) payload.status = values.status;
  return payload;
}

interface VariantFormProps {
  mode: "create" | "edit";
  productId: string;
  initialData?: Variant;
}

export function VariantForm({
  mode,
  productId,
  initialData,
}: VariantFormProps) {
  const router = useRouter();
  const createMutation = useCreateVariant();
  const updateMutation = useUpdateVariant(initialData?.id ?? "");
  const mutation = mode === "create" ? createMutation : updateMutation;

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: toFormValues(initialData),
  });

  const readonly = mode === "edit";

  function applyServerErrors(error: unknown) {
    const axios = error as AxiosError<Record<string, unknown>>;
    const body = axios?.response?.data;
    if (!body || typeof body !== "object") return;
    for (const [beField, messages] of Object.entries(body)) {
      const formField = BE_TO_FORM_FIELD[beField];
      if (!formField) continue;
      const message = Array.isArray(messages)
        ? String(messages[0])
        : String(messages);
      form.setError(formField, { type: "server", message });
    }
  }

  function onSubmit(values: FormValues) {
    const backToList = () =>
      router.push(`/admin/products/${productId}/variants`);

    if (mode === "create") {
      createMutation.mutate(toCreatePayload(values, productId), {
        onSuccess: backToList,
        onError: applyServerErrors,
      });
      return;
    }

    // Edit: chỉ patch dirty fields (4 field mutable).
    const payload = toUpdatePayload(values, form.formState.dirtyFields);
    if (Object.keys(payload).length === 0) {
      backToList();
      return;
    }
    updateMutation.mutate(payload, {
      onSuccess: backToList,
      onError: applyServerErrors,
    });
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="max-w-2xl space-y-6"
      >
        {/* Axes: 3 nhóm material / color / size — readonly ở edit mode. */}
        <div className="space-y-4">
          <h2 className="text-sm font-medium text-muted-foreground">
            Axes {readonly && "(immutable)"}
          </h2>

          <div className="grid grid-cols-[1fr_120px] gap-4">
            <FormField
              control={form.control}
              name="material_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tên material *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Polylactic Acid"
                      disabled={readonly}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="material_code3"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Code 3 *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="PLA"
                      disabled={readonly}
                      onChange={(e) =>
                        field.onChange(e.target.value.toUpperCase())
                      }
                      className="font-mono"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="grid grid-cols-[1fr_120px] gap-4">
            <FormField
              control={form.control}
              name="color_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tên color *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="Red" disabled={readonly} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="color_code3"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Code 3 *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="RED"
                      disabled={readonly}
                      onChange={(e) =>
                        field.onChange(e.target.value.toUpperCase())
                      }
                      className="font-mono"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="size_preset"
            render={({ field }) => (
              <FormItem className="max-w-[200px]">
                <FormLabel>Size *</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="M / L / XL / 12cm"
                    disabled={readonly}
                  />
                </FormControl>
                <FormDescription>1-8 ký tự alphanumeric.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* SKU preview ở edit mode */}
        {readonly && initialData && (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">SKU (auto-gen)</p>
            <p className="font-mono text-sm">{initialData.sku}</p>
          </div>
        )}

        {/* Pricing + status */}
        <div className="space-y-4">
          <h2 className="text-sm font-medium text-muted-foreground">Pricing</h2>
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="base_price"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Giá bán (VND) *</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="number"
                      step="1000"
                      min="0"
                      placeholder="150000"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="cost_price"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Cost (VND)</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="number"
                      step="1000"
                      min="0"
                      placeholder="(tuỳ chọn)"
                    />
                  </FormControl>
                  <FormDescription>Để trống = chưa biết.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem className="max-w-[200px]">
                <FormLabel>Status</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="archived">Archived</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? "Đang lưu..."
              : mode === "create"
                ? "Tạo variant"
                : "Lưu thay đổi"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              router.push(`/admin/products/${productId}/variants`)
            }
          >
            Huỷ
          </Button>
        </div>
      </form>
    </Form>
  );
}
