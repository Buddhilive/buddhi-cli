"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type {
  DownloadRequest,
  DownloadStartResponse,
  CancelResponse,
} from "@/types/models";

/** Start a model download. Invalidates the downloads list on success. */
export function useStartDownload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (req: DownloadRequest) =>
      apiFetch<DownloadStartResponse>(`${API_BASE}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloads"] });
    },
  });
}

/** Cancel an active download. Invalidates the downloads list on success. */
export function useCancelDownload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (downloadId: string) =>
      apiFetch<CancelResponse>(
        `${API_BASE}/download/${downloadId}/cancel`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloads"] });
    },
  });
}
