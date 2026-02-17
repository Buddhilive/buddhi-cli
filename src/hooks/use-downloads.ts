"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type { DownloadListResponse } from "@/types/models";

/**
 * Fetch all active/recent downloads.
 * Polls every 3 seconds when there are active downloads for near-real-time updates.
 */
export function useDownloads(hasActive: boolean = false) {
  return useQuery({
    queryKey: ["downloads"],
    queryFn: () => apiFetch<DownloadListResponse>(`${API_BASE}/downloads`),
    refetchInterval: hasActive ? 3000 : false,
  });
}
