import { Suspense } from "react";

import { VariantEditClient } from "./_components/variant-edit-client";

export const metadata = {
  title: "Sửa Variant | 3D Printing PIM",
};

export default function EditVariantPage({
  params,
}: {
  params: { id: string; vid: string };
}) {
  return (
    <div className="p-6">
      <Suspense
        fallback={
          <div className="text-sm text-muted-foreground">Loading...</div>
        }
      >
        <VariantEditClient productId={params.id} variantId={params.vid} />
      </Suspense>
    </div>
  );
}
