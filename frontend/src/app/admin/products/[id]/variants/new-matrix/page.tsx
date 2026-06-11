import Link from "next/link";

import { VariantMatrixForm } from "../_components/variant-matrix-form";

export const metadata = {
  title: "Matrix variants | 3D Printing PIM",
};

export default function NewMatrixPage({
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
        <h1 className="mt-2 text-2xl font-semibold">
          Tạo nhiều variants (matrix)
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Chọn các giá trị cho mỗi trục → sinh N × M × P variants 1 lần. Giá
          bán + status chung cho cả batch (có thể sửa từng variant sau).
        </p>
      </div>
      <VariantMatrixForm productId={params.id} />
    </div>
  );
}
