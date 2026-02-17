"use client";

import { DownloadCard } from "@/components/models/download-card";
import type { DownloadProgress } from "@/types/models";

interface DownloadListProps {
  downloads: DownloadProgress[];
}

/** Renders a list of download cards, active downloads first. */
export function DownloadList({ downloads }: DownloadListProps) {
  // Sort: active (pending/downloading) first, then completed/failed/cancelled
  const sorted = [...downloads].sort((a, b) => {
    const activeStates = new Set(["pending", "downloading"]);
    const aActive = activeStates.has(a.status) ? 0 : 1;
    const bActive = activeStates.has(b.status) ? 0 : 1;
    return aActive - bActive;
  });

  return (
    <div className="space-y-3">
      {sorted.map((dl) => (
        <DownloadCard key={dl.download_id} download={dl} />
      ))}
    </div>
  );
}
