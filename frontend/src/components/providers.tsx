"use client";

/**
 * Client-side providers (TanStack Query, Toast).
 *
 * Mount trong app/layout.tsx để mọi route thuộc cây này có:
 *   - useQuery / useMutation
 *   - toast() từ sonner
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Toaster } from "sonner";

import { bootstrapAccessTokenFromStorage } from "@/lib/api/client";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    bootstrapAccessTokenFromStorage();
  }, []);

  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}
