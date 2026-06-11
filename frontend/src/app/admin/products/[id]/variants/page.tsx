/**
 * Variants list page — nested dưới Product.
 *
 * Server shell render header + client list. Client component fetch product
 * name + variant list, render filter + table.
 */

import { Suspense } from "react";

import { VariantsListClient } from "./_components/variants-list-client";

export const metadata = {
  title: "Variants | 3D Printing PIM",
};

export default function VariantsListPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="p-6">
      <Suspense
        fallback={
          <div className="text-sm text-muted-foreground">Loading...</div>
        }
      >
        <VariantsListClient productId={params.id} />
      </Suspense>
    </div>
  );
}
