"use client";

import { CheckCircle2, XCircle, Ban, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useDownloadProgress } from "@/hooks/use-download-progress";
import { useCancelDownload } from "@/hooks/use-download-actions";
import { formatBytes } from "@/lib/format";
import { getErrorMessage } from "@/lib/api-client";
import type { DownloadProgress } from "@/types/models";

interface DownloadCardProps {
  download: DownloadProgress;
}

/**
 * Card for a single download showing real-time progress via SSE.
 * Active downloads open their own SSE connection for live updates.
 */
export function DownloadCard({ download }: DownloadCardProps) {
  const queryClient = useQueryClient();
  const cancelDownload = useCancelDownload();

  const isActive =
    download.status === "downloading" || download.status === "pending";

  // Open SSE connection only for active downloads
  const { progress: sseProgress } = useDownloadProgress(
    isActive ? download.download_id : null,
    {
      onComplete: (p) => {
        toast.success(`Download complete: ${p.filename}`);
        queryClient.invalidateQueries({ queryKey: ["downloads"] });
        queryClient.invalidateQueries({ queryKey: ["library"] });
      },
      onFailed: (p) => {
        toast.error(`Download failed: ${p.error_message || p.filename}`);
        queryClient.invalidateQueries({ queryKey: ["downloads"] });
      },
      onCancelled: (p) => {
        toast.info(`Download cancelled: ${p.filename}`);
        queryClient.invalidateQueries({ queryKey: ["downloads"] });
      },
    }
  );

  // Use SSE progress if available, otherwise fall back to the polled data
  const current = sseProgress ?? download;

  const handleCancel = () => {
    cancelDownload.mutate(download.download_id, {
      onError: (err) => {
        toast.error(getErrorMessage(err, "Failed to cancel download"));
      },
    });
  };

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-2">
        {/* Header: filename + status badge */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{current.filename}</p>
            <p className="text-xs text-muted-foreground truncate">
              {current.repo_id}
            </p>
          </div>
          <StatusBadge status={current.status} />
        </div>

        {/* Progress bar for active downloads */}
        {isActive && (
          <>
            <Progress value={current.progress} className="h-2" />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {formatBytes(current.downloaded_bytes)} / {formatBytes(current.total_bytes)}
              </span>
              <span>{current.progress.toFixed(1)}%</span>
            </div>
          </>
        )}

        {/* Completed info */}
        {current.status === "completed" && current.total_bytes > 0 && (
          <p className="text-xs text-muted-foreground">
            {formatBytes(current.total_bytes)}
          </p>
        )}

        {/* Error message */}
        {current.status === "failed" && current.error_message && (
          <p className="text-xs text-destructive">{current.error_message}</p>
        )}

        {/* Cancel button for active downloads */}
        {isActive && (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancel}
              disabled={cancelDownload.isPending}
            >
              {cancelDownload.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Ban className="h-4 w-4 mr-1" />
              )}
              Cancel
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="default" className="bg-green-600 hover:bg-green-600 text-white gap-1">
          <CheckCircle2 className="h-3 w-3" />
          Completed
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    case "cancelled":
      return (
        <Badge variant="secondary" className="gap-1">
          <Ban className="h-3 w-3" />
          Cancelled
        </Badge>
      );
    case "downloading":
      return (
        <Badge variant="default" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Downloading
        </Badge>
      );
    default:
      return <Badge variant="outline">Pending</Badge>;
  }
}
