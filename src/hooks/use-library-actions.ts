"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type { DeleteResponse } from "@/types/models";

/** Delete a downloaded model. Invalidates the library query on success. */
export function useDeleteModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (modelId: number) =>
      apiFetch<DeleteResponse>(`${API_BASE}/library/${modelId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] });
    },
  });
}
