"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type { ModelLibraryResponse } from "@/types/models";

/** Fetch the list of locally downloaded models. */
export function useLibrary() {
  return useQuery({
    queryKey: ["library"],
    queryFn: () => apiFetch<ModelLibraryResponse>(`${API_BASE}/library`),
  });
}
