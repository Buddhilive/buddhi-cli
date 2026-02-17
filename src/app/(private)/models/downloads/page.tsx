"use client";

import { useMemo } from "react";
import { AlertCircle, Download } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { DownloadList } from "@/components/models/download-list";
import { EmptyState } from "@/components/models/empty-state";
import { useDownloads } from "@/hooks/use-downloads";
import { getErrorMessage } from "@/lib/api-client";

export default function DownloadsPage() {
  const { data, isLoading, isError, error } = useDownloads(true);

  const activeCount = useMemo(() => {
    if (!data) return 0;
    return data.downloads.filter(
      (d) => d.status === "downloading" || d.status === "pending"
    ).length;
  }, [data]);

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Downloads</h1>
        <p className="text-sm text-muted-foreground">
          {activeCount > 0
            ? `${activeCount} active download${activeCount > 1 ? "s" : ""}`
            : "Track your model downloads"}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border p-4 space-y-3">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="h-2 w-full" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {getErrorMessage(error, "Failed to load downloads.")}
          </AlertDescription>
        </Alert>
      )}

      {/* Downloads list */}
      {data && data.downloads.length > 0 && (
        <DownloadList downloads={data.downloads} />
      )}

      {/* Empty state */}
      {data && data.downloads.length === 0 && (
        <EmptyState
          icon={Download}
          title="No downloads"
          description="Downloads you start from the search page will appear here."
          action={{ label: "Search Models", href: "/models/search" }}
        />
      )}
    </div>
  );
}
