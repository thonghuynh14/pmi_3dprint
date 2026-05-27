/**
 * Edit product page (server shell).
 *
 * Data fetch xảy ra client-side (JWT trong browser storage, không có
 * SSR token). Page chỉ extract param id, pass cho client component.
 */

import { ProductEditClient } from "./_components/product-edit-client";

export const metadata = {
  title: "Sửa Product | 3D Printing PIM",
};

export default function EditProductPage({
  params,
}: {
  params: { id: string };
}) {
  return <ProductEditClient id={params.id} />;
}
