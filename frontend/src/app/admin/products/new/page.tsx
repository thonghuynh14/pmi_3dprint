import Link from "next/link";

import { ProductForm } from "../_components/product-form";

export const metadata = {
  title: "Tạo Product | 3D Printing PIM",
};

export default function NewProductPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <Link
          href="/admin/products"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Products
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Tạo product mới</h1>
      </div>
      <ProductForm mode="create" />
    </div>
  );
}
