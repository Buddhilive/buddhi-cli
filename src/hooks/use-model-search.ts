"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type { ModelSearchResponse, SearchParams } from "@/types/models";

/**
 * Search for GGUF models on HuggingFace via the proxy.
 * Results are cached and previous data is kept during pagination transitions.
 */
export function useModelSearch(params: SearchParams) {
  const searchParams = new URLSearchParams({
    query: params.query,
    sort: params.sort,
    direction: String(params.direction),
    page: String(params.page),
    page_size: String(params.page_size),
    ...(params.author ? { author: params.author } : {}),
  });

  return useQuery({
    queryKey: ["model-search", params],
    queryFn: () =>
      apiFetch<ModelSearchResponse>(
        `${API_BASE}/search?${searchParams.toString()}`
      ),
    placeholderData: keepPreviousData,
    enabled: params.query.length > 0,
  });
}
