/**
 * Products list page (server component shell).
 *
 * Data fetch + UI tương tác xảy ra trong client component (cần JWT
 * trong browser-storage). Page chỉ render header + client wrapper.
 */

import { Suspense } from "react";

import { ProductsListClient } from "./_components/products-list-client";

export const metadata = {
  title: "Products | 3D Printing PIM",
};

export default function ProductsPage() {
  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Products</h1>
          <p className="text-sm text-muted-foreground">
            Quản lý sản phẩm gốc của catalog.
          </p>
        </div>
      </div>

      <Suspense fallback={<div className="text-sm text-muted-foreground">Loading...</div>}>
        <ProductsListClient />
      </Suspense>
    </div>
  );
}
