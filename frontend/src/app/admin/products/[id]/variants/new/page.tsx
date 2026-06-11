import Link from "next/link";

import { VariantForm } from "../_components/variant-form";

export const metadata = {
  title: "Tạo Variant | 3D Printing PIM",
};

export default function NewVariantPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="p-6">
      <div className="mb-6">
        <Link
          href={`/admin/products/${params.id}/variants`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Variants
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Tạo variant mới</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          1 tổ hợp material × color × size. Muốn tạo nhiều cùng lúc → dùng
          &quot;Thêm matrix&quot;.
        </p>
      </div>
      <VariantForm mode="create" productId={params.id} />
    </div>
  );
}
