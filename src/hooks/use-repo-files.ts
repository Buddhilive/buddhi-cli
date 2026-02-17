"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { API_BASE } from "@/lib/constants";
import type { RepoFilesResponse } from "@/types/models";

/**
 * Fetch the list of GGUF files in a HuggingFace repository.
 * Only runs when enabled (e.g., when the file picker dialog is open).
 */
export function useRepoFiles(repoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["repo-files", repoId],
    queryFn: () =>
      apiFetch<RepoFilesResponse>(
        `${API_BASE}/files?repo_id=${encodeURIComponent(repoId)}`
      ),
    enabled,
    staleTime: 5 * 60_000,
  });
}
