---
name: nextjs-frontend
description: Sinh code Next.js (App Router) cho frontend admin/POS của hệ thống quản lý SKU in 3D, gọi API Django DRF. Use this skill whenever the user mentions "frontend", "FE", "Next.js", "React component", "page", "UI", "admin panel", "POS UI", or asks to build any client-side feature — even casually like "làm màn hình X", "code FE cho ...", "tạo form Y", "tạo trang Z". Also triggers for data fetching with TanStack Query, forms with react-hook-form + zod, tables with TanStack Table, 3D model viewer integration, file upload UI, and shadcn/ui component usage.
---

# Next.js Frontend Generator

Skill này sinh code Next.js 14 (App Router) cho admin panel + POS app của dự án 3D Printing PIM. Backend là Django DRF qua REST API.

## Stack cố định

- **Next.js 14+** App Router (server components + client components)
- **TypeScript** strict mode
- **Tailwind CSS** + **shadcn/ui** (Radix-based primitives)
- **TanStack Query (React Query) v5** cho data fetching/caching
- **react-hook-form + zod** cho forms + validation
- **TanStack Table v8** cho data tables
- **Axios** hoặc native `fetch` cho HTTP (axios khuyến nghị cho interceptor)
- **`<model-viewer>`** (Google web component) cho 3D preview
- **next-intl** cho i18n (VN + EN)
- **Zustand** cho client-state nhẹ (auth, UI state)
- **date-fns** cho date utils

## Project structure

```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
├── components.json          # shadcn config
├── src/
│   ├── app/
│   │   ├── (auth)/          # login, register
│   │   ├── (admin)/         # admin panel - protected
│   │   │   ├── layout.tsx
│   │   │   ├── products/
│   │   │   ├── variants/
│   │   │   ├── design-files/
│   │   │   ├── materials/
│   │   │   ├── printers/
│   │   │   ├── poc/
│   │   │   ├── channels/
│   │   │   └── orders/
│   │   ├── (pos)/           # POS app - separate layout
│   │   │   ├── layout.tsx
│   │   │   ├── checkout/
│   │   │   └── orders/
│   │   ├── api/             # Next.js route handlers (BFF only if needed)
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/              # shadcn primitives
│   │   ├── forms/           # reusable form fields
│   │   ├── tables/          # reusable table patterns
│   │   ├── product/
│   │   ├── variant/
│   │   ├── design-file/
│   │   ├── viewer-3d/
│   │   └── layout/
│   ├── lib/
│   │   ├── api/             # API client + endpoints
│   │   │   ├── client.ts    # axios instance
│   │   │   ├── products.ts
│   │   │   ├── variants.ts
│   │   │   └── ...
│   │   ├── hooks/           # React Query hooks
│   │   ├── schemas/         # zod schemas (shared with API contracts)
│   │   ├── types/           # TS types (generated từ DRF OpenAPI)
│   │   ├── utils/
│   │   └── constants/
│   ├── stores/              # Zustand stores
│   ├── messages/            # i18n strings
│   │   ├── vi.json
│   │   └── en.json
│   └── middleware.ts        # Auth + i18n routing
└── public/
    └── ...
```

## Nguyên tắc

### 1. Server Components mặc định, Client Components khi cần

Mark `'use client'` chỉ khi cần:
- State (`useState`, `useReducer`)
- Effects (`useEffect`)
- Browser API
- Event handlers
- Third-party libs cần client

Server Component cho:
- Initial data fetch
- SEO-relevant pages
- Static content

```tsx
// app/(admin)/products/page.tsx — Server Component
import { getProducts } from '@/lib/api/products.server';
import { ProductListClient } from './_components/product-list-client';

export default async function ProductsPage({ 
  searchParams 
}: { 
  searchParams: { page?: string; status?: string } 
}) {
  // Server-side fetch with cookies forwarded
  const initialData = await getProducts({
    page: Number(searchParams.page ?? 1),
    status: searchParams.status,
  });
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Sản phẩm</h1>
      <ProductListClient initialData={initialData} />
    </div>
  );
}
```

```tsx
// app/(admin)/products/_components/product-list-client.tsx
'use client';

import { useProducts } from '@/lib/hooks/use-products';
import { DataTable } from '@/components/tables/data-table';
import { columns } from './columns';

export function ProductListClient({ initialData }: { initialData: PaginatedProducts }) {
  const { data, isLoading } = useProducts({ initialData });
  
  return <DataTable columns={columns} data={data?.results ?? []} loading={isLoading} />;
}
```

### 2. API client + React Query hooks

```ts
// lib/api/client.ts
import axios, { AxiosError } from 'axios';
import { getAuthToken, refreshAuthToken } from '@/lib/auth';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptors
apiClient.interceptors.request.use(async (config) => {
  const token = await getAuthToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      await refreshAuthToken();
      return apiClient.request(error.config!);
    }
    return Promise.reject(error);
  }
);

// Error type
export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
}
```

```ts
// lib/api/variants.ts
import { apiClient } from './client';
import type { Variant, VariantCreateInput, PaginatedResponse } from '@/lib/types';

export const variantsApi = {
  list: (params: { page?: number; status?: string; product_id?: string }) =>
    apiClient.get<PaginatedResponse<Variant>>('/v1/variants/', { params })
      .then(r => r.data),
  
  get: (id: string) =>
    apiClient.get<Variant>(`/v1/variants/${id}/`).then(r => r.data),
  
  create: (data: VariantCreateInput) =>
    apiClient.post<Variant>('/v1/variants/', data).then(r => r.data),
  
  update: (id: string, data: Partial<VariantCreateInput>) =>
    apiClient.patch<Variant>(`/v1/variants/${id}/`, data).then(r => r.data),
  
  delete: (id: string) =>
    apiClient.delete(`/v1/variants/${id}/`),
  
  publishToChannel: (id: string, channel: 'shopee' | 'lazada' | 'tiki') =>
    apiClient.post(`/v1/variants/${id}/publish_to_channel/`, { channel })
      .then(r => r.data),
  
  bulkGenerate: (productId: string, axesMatrix: Record<string, string[]>) =>
    apiClient.post(`/v1/products/${productId}/generate_variants/`, { axes: axesMatrix })
      .then(r => r.data),
};
```

```ts
// lib/hooks/use-variants.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { variantsApi } from '@/lib/api/variants';
import { toast } from 'sonner';

export const variantKeys = {
  all: ['variants'] as const,
  lists: () => [...variantKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...variantKeys.lists(), filters] as const,
  details: () => [...variantKeys.all, 'detail'] as const,
  detail: (id: string) => [...variantKeys.details(), id] as const,
};

export function useVariants(params: Parameters<typeof variantsApi.list>[0], options?: { initialData?: any }) {
  return useQuery({
    queryKey: variantKeys.list(params),
    queryFn: () => variantsApi.list(params),
    initialData: options?.initialData,
    staleTime: 60_000,
  });
}

export function useVariant(id: string) {
  return useQuery({
    queryKey: variantKeys.detail(id),
    queryFn: () => variantsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: variantsApi.create,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: variantKeys.lists() });
      toast.success(`Tạo variant ${data.sku} thành công`);
    },
    onError: (error: AxiosError<ApiError>) => {
      const apiError = error.response?.data;
      if (apiError?.error_code === 'LICENSE_BLOCKS_COMMERCIAL') {
        toast.error('License file không cho phép bán thương mại');
      } else {
        toast.error(apiError?.message ?? 'Lỗi không xác định');
      }
    },
  });
}
```

### 3. Forms with react-hook-form + zod

```tsx
// components/variant/variant-create-form.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateVariant } from '@/lib/hooks/use-variants';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const variantCreateSchema = z.object({
  product_id: z.string().uuid(),
  axes: z.object({
    material_id: z.string().uuid().optional(),
    material_color: z.string().max(32).optional(),
    size_preset: z.string().max(16).optional(),
    layer_resolution_mm: z.number().positive().optional(),
    infill_percent: z.number().int().min(0).max(100).optional(),
  }),
  base_price: z.number().nonnegative(),
  design_file_id: z.string().uuid().optional(),
});

type VariantCreateValues = z.infer<typeof variantCreateSchema>;

export function VariantCreateForm({ productId, onSuccess }: { productId: string; onSuccess?: () => void }) {
  const createMutation = useCreateVariant();
  
  const form = useForm<VariantCreateValues>({
    resolver: zodResolver(variantCreateSchema),
    defaultValues: {
      product_id: productId,
      axes: {},
      base_price: 0,
    },
  });
  
  const onSubmit = (values: VariantCreateValues) => {
    createMutation.mutate(values, { onSuccess: () => onSuccess?.() });
  };
  
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="axes.material_color"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Màu vật liệu</FormLabel>
              <FormControl><Input {...field} placeholder="Red, Blue..." /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <FormField
          control={form.control}
          name="base_price"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Giá bán (VND)</FormLabel>
              <FormControl>
                <Input 
                  type="number" 
                  {...field}
                  onChange={(e) => field.onChange(Number(e.target.value))}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <Button type="submit" disabled={createMutation.isPending}>
          {createMutation.isPending ? 'Đang tạo...' : 'Tạo variant'}
        </Button>
      </form>
    </Form>
  );
}
```

### 4. Data table pattern

Xem `references/data_table.md`.

### 5. 3D viewer integration

```tsx
// components/viewer-3d/stl-glb-viewer.tsx
'use client';

import { useEffect, useRef } from 'react';
import Script from 'next/script';

interface Props {
  glbUrl: string;
  posterUrl?: string;
  alt?: string;
  className?: string;
}

export function StlGlbViewer({ glbUrl, posterUrl, alt, className }: Props) {
  return (
    <>
      <Script
        type="module"
        src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"
        strategy="afterInteractive"
      />
      {/* @ts-expect-error - model-viewer is a web component */}
      <model-viewer
        src={glbUrl}
        poster={posterUrl}
        alt={alt}
        camera-controls
        auto-rotate
        ar
        ar-modes="webxr scene-viewer quick-look"
        shadow-intensity="1"
        class={className}
        style={{ width: '100%', height: '400px', backgroundColor: '#f3f4f6' }}
      />
    </>
  );
}

// TypeScript declarations
declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          src: string;
          'camera-controls'?: boolean;
          'auto-rotate'?: boolean;
          ar?: boolean;
          'ar-modes'?: string;
          poster?: string;
          alt?: string;
          'shadow-intensity'?: string;
        },
        HTMLElement
      >;
    }
  }
}
```

### 6. File upload (STL)

```tsx
// components/design-file/upload-stl.tsx
'use client';

import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export function UploadStl({ onUploaded }: { onUploaded: (fileId: string) => void }) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'model/stl': ['.stl'],
      'model/obj': ['.obj'],
      'model/3mf': ['.3mf'],
    },
    maxSize: 500 * 1024 * 1024, // 500MB
    maxFiles: 1,
    onDrop: async (files) => {
      const file = files[0];
      if (!file) return;
      
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        // Direct upload to backend → backend pre-signs S3 PUT
        const res = await apiClient.post('/v1/design-files/upload/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => {
            if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
          },
        });
        toast.success(`Upload ${file.name} thành công`);
        onUploaded(res.data.id);
      } catch (err) {
        toast.error('Upload lỗi');
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
  });
  
  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
        ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}`}
    >
      <input {...getInputProps()} />
      <p className="text-sm text-muted-foreground">
        {isDragActive ? 'Thả file vào đây...' : 'Kéo thả file STL/OBJ/3MF hoặc click để chọn'}
      </p>
      <p className="text-xs text-muted-foreground mt-2">Max 500MB</p>
      {uploading && <Progress value={progress} className="mt-4" />}
    </div>
  );
}
```

### 7. Variant matrix generator UI

Đây là 1 UI quan trọng cần làm đúng: user chọn axes (color, size...) → preview 6/15/30 variants → adjust → save.

```tsx
// app/(admin)/products/[id]/variants/_components/variant-matrix.tsx
'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface AxisValue { id: string; label: string; }
interface Axis { name: string; label: string; values: AxisValue[]; }

export function VariantMatrix({ productId, availableAxes }: { productId: string; availableAxes: Axis[] }) {
  const [selectedAxes, setSelectedAxes] = useState<Record<string, AxisValue[]>>({});
  
  const cartesianProduct = useMemo(() => {
    const axes = Object.entries(selectedAxes).filter(([, vs]) => vs.length > 0);
    if (axes.length === 0) return [];
    
    return axes.reduce<Record<string, string>[]>(
      (acc, [name, values]) => {
        if (acc.length === 0) return values.map(v => ({ [name]: v.label }));
        return acc.flatMap(combo => values.map(v => ({ ...combo, [name]: v.label })));
      },
      []
    );
  }, [selectedAxes]);
  
  const variantCount = cartesianProduct.length;
  const tooMany = variantCount > 50;
  
  return (
    <div className="space-y-6">
      {availableAxes.map(axis => (
        <div key={axis.name}>
          <h3 className="font-medium mb-2">{axis.label}</h3>
          <div className="flex flex-wrap gap-2">
            {axis.values.map(v => {
              const selected = selectedAxes[axis.name]?.some(s => s.id === v.id);
              return (
                <Badge
                  key={v.id}
                  variant={selected ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => {
                    setSelectedAxes(prev => {
                      const current = prev[axis.name] ?? [];
                      const next = selected ? current.filter(x => x.id !== v.id) : [...current, v];
                      return { ...prev, [axis.name]: next };
                    });
                  }}
                >
                  {v.label}
                </Badge>
              );
            })}
          </div>
        </div>
      ))}
      
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm">
            Sẽ tạo <strong>{variantCount}</strong> variants
            {tooMany && (
              <span className="text-destructive ml-2">
                ⚠️ Quá nhiều variants - hãy cân nhắc giảm axes
              </span>
            )}
          </p>
          <Button disabled={variantCount === 0 || tooMany}>
            Generate {variantCount} variants
          </Button>
        </div>
        
        {variantCount > 0 && variantCount <= 20 && (
          <div className="max-h-96 overflow-y-auto border rounded">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  {Object.keys(cartesianProduct[0] ?? {}).map(k => (
                    <th key={k} className="px-3 py-2 text-left">{k}</th>
                  ))}
                  <th className="px-3 py-2 text-left">SKU (preview)</th>
                </tr>
              </thead>
              <tbody>
                {cartesianProduct.map((row, i) => (
                  <tr key={i} className="border-t">
                    {Object.values(row).map((v, j) => (
                      <td key={j} className="px-3 py-2">{v}</td>
                    ))}
                    <td className="px-3 py-2 font-mono text-xs">
                      {/* Preview SKU - call API or compute locally */}
                      ...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
```

## Reference files

- `references/data_table.md` — TanStack Table pattern đầy đủ
- `references/auth_pattern.md` — JWT + refresh + middleware
- `references/pos_offline.md` — IndexedDB + Service Worker
- `references/i18n.md` — next-intl setup

## Anti-patterns

❌ `useEffect` để fetch data → ✅ React Query  
❌ `useState` để lưu server data → ✅ React Query cache  
❌ Mọi component đều `'use client'` → ✅ Server Component mặc định  
❌ Inline fetch trong component → ✅ qua `lib/api/*` + hook  
❌ Validate form bằng tay → ✅ zod + react-hook-form  
❌ Hard-code màu, spacing → ✅ Tailwind tokens, design system  
❌ Bỏ qua loading/error state → ✅ luôn handle 3 state: loading/error/success  
❌ Type `any` → ✅ generate types từ DRF OpenAPI (drf-spectacular + openapi-typescript)  
❌ Mix tiếng Việt cứng trong code → ✅ qua i18n
