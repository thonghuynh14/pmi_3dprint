"use client";

/**
 * Product form — shared create + edit.
 *
 * UI dùng tagsInput (comma-separated) + attributesInput (JSON string)
 * cho dễ nhập; transform sang array/object khi submit. BE field errors
 * (400) được map ngược vào RHF setError để hiển thị inline.
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
import { Textarea } from "@/components/ui/textarea";
import { useCreateProduct, useUpdateProduct } from "@/lib/hooks/use-products";
import type { ProductInput } from "@/lib/schemas/product";
import type { Product } from "@/lib/types/product";
import { slugify } from "@/lib/utils/slugify";

const SKU_ROOT_RE = /^[A-Z0-9]{3,8}$/;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function isValidJsonObject(s: string): boolean {
  if (!s.trim()) return true;
  try {
    const v: unknown = JSON.parse(s);
    return typeof v === "object" && v !== null && !Array.isArray(v);
  } catch {
    return false;
  }
}

const formSchema = z.object({
  name: z.string().min(1, "Tên không được trống.").max(200),
  slug: z
    .string()
    .max(220)
    .refine((v) => v === "" || SLUG_RE.test(v), "Slug không hợp lệ."),
  sku_root: z
    .string()
    .min(3, "Tối thiểu 3 ký tự.")
    .max(8, "Tối đa 8 ký tự.")
    .refine((v) => SKU_ROOT_RE.test(v.toUpperCase()), "Chỉ chữ và số."),
  status: z.enum(["draft", "active", "archived"]),
  short_description: z.string(),
  long_description: z.string(),
  brand: z.string().max(100),
  tagsInput: z.string(),
  attributesInput: z.string().refine(isValidJsonObject, "JSON object không hợp lệ."),
});

type FormValues = z.infer<typeof formSchema>;

// Map BE field name → form field name (khác nhau ở tags/attributes).
const BE_TO_FORM_FIELD: Record<string, keyof FormValues> = {
  name: "name",
  slug: "slug",
  sku_root: "sku_root",
  status: "status",
  short_description: "short_description",
  long_description: "long_description",
  brand: "brand",
  tags: "tagsInput",
  attributes: "attributesInput",
};

// Map form field name → payload (ProductInput) key — cho dirty-fields PATCH.
const FORM_TO_PAYLOAD_KEY: Record<keyof FormValues, keyof ProductInput> = {
  name: "name",
  slug: "slug",
  sku_root: "sku_root",
  status: "status",
  short_description: "short_description",
  long_description: "long_description",
  brand: "brand",
  tagsInput: "tags",
  attributesInput: "attributes",
};

function toFormValues(product?: Product): FormValues {
  return {
    name: product?.name ?? "",
    slug: product?.slug ?? "",
    sku_root: product?.sku_root ?? "",
    status: product?.status ?? "draft",
    short_description: product?.short_description ?? "",
    long_description: product?.long_description ?? "",
    brand: product?.brand ?? "",
    tagsInput: product?.tags.join(", ") ?? "",
    attributesInput: product?.attributes
      ? JSON.stringify(product.attributes, null, 2)
      : "{}",
  };
}

function toPayload(values: FormValues): ProductInput {
  return {
    name: values.name,
    slug: values.slug,
    sku_root: values.sku_root,
    status: values.status,
    short_description: values.short_description,
    long_description: values.long_description,
    brand: values.brand,
    tags: values.tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
    attributes: values.attributesInput.trim()
      ? (JSON.parse(values.attributesInput) as Record<string, unknown>)
      : {},
  };
}

interface ProductFormProps {
  mode: "create" | "edit";
  initialData?: Product;
}

export function ProductForm({ mode, initialData }: ProductFormProps) {
  const router = useRouter();
  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct(initialData?.id ?? "");
  const mutation = mode === "create" ? createMutation : updateMutation;

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: toFormValues(initialData),
  });

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
    const fullPayload = toPayload(values);

    // Edit mode: chỉ PATCH field đã thay đổi (dirty) → match SPEC AC-7.
    let payload: Partial<ProductInput> = fullPayload;
    if (mode === "edit") {
      const dirty = form.formState.dirtyFields;
      payload = {};
      for (const formKey of Object.keys(dirty) as (keyof FormValues)[]) {
        const payloadKey = FORM_TO_PAYLOAD_KEY[formKey];
        // @ts-expect-error -- key đồng nhất giữa 2 record
        payload[payloadKey] = fullPayload[payloadKey];
      }
      if (Object.keys(payload).length === 0) {
        // Không có gì đổi → quay về list, không gọi API.
        router.push("/admin/products");
        return;
      }
    }

    mutation.mutate(payload as never, {
      onSuccess: () => router.push("/admin/products"),
      onError: applyServerErrors,
    });
  }

  function handleNameBlur() {
    // Auto-fill slug từ name nếu slug đang trống.
    if (!form.getValues("slug")) {
      form.setValue("slug", slugify(form.getValues("name")), {
        shouldValidate: true,
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-2xl space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tên sản phẩm *</FormLabel>
              <FormControl>
                <Input {...field} onBlur={handleNameBlur} placeholder="Dragon Figure" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="slug"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Slug</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="dragon-figure" />
                </FormControl>
                <FormDescription>Để trống → tự sinh từ tên.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="sku_root"
            render={({ field }) => (
              <FormItem>
                <FormLabel>SKU root *</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="DRAGON"
                    onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                  />
                </FormControl>
                <FormDescription>3-8 ký tự hoa/số.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
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

          <FormField
            control={form.control}
            name="brand"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Brand</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="(tuỳ chọn)" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="short_description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Mô tả ngắn</FormLabel>
              <FormControl>
                <Textarea {...field} rows={2} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="long_description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Mô tả chi tiết (markdown)</FormLabel>
              <FormControl>
                <Textarea {...field} rows={6} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="tagsInput"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tags</FormLabel>
              <FormControl>
                <Input {...field} placeholder="figure, dragon, fantasy" />
              </FormControl>
              <FormDescription>Phân cách bằng dấu phẩy.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="attributesInput"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Attributes (JSON)</FormLabel>
              <FormControl>
                <Textarea {...field} rows={4} className="font-mono text-sm" />
              </FormControl>
              <FormDescription>
                JSON object, vd: {`{ "scale": "1:10", "weight_g": 120 }`}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? "Đang lưu..."
              : mode === "create"
                ? "Tạo product"
                : "Lưu thay đổi"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push("/admin/products")}
          >
            Huỷ
          </Button>
        </div>
      </form>
    </Form>
  );
}
