"use client";

import { useState } from "react";
import { AlertCircle, HardDrive } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { LibraryTable } from "@/components/models/library-table";
import { DeleteModelDialog } from "@/components/models/delete-model-dialog";
import { EmptyState } from "@/components/models/empty-state";
import { useLibrary } from "@/hooks/use-library";
import { useDeleteModel } from "@/hooks/use-library-actions";
import { formatBytes } from "@/lib/format";
import { getErrorMessage } from "@/lib/api-client";
import type { DownloadedModel } from "@/types/models";

export default function LibraryPage() {
  const { data, isLoading, isError, error } = useLibrary();
  const deleteModel = useDeleteModel();

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<DownloadedModel | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const handleDeleteClick = (model: DownloadedModel) => {
    setDeleteTarget(model);
    setDeleteOpen(true);
  };

  const handleDeleteConfirm = (modelId: number) => {
    deleteModel.mutate(modelId, {
      onSuccess: (res) => {
        toast.success(res.message);
        setDeleteOpen(false);
        setDeleteTarget(null);
      },
      onError: (err) => {
        toast.error(getErrorMessage(err, "Failed to delete model"));
      },
    });
  };

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Model Library
          </h1>
          <p className="text-sm text-muted-foreground">
            {data
              ? `${data.models.length} model${data.models.length !== 1 ? "s" : ""} — ${formatBytes(data.total_size)} total`
              : "Manage your downloaded models"}
          </p>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="rounded-md border">
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-8" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {getErrorMessage(error, "Failed to load library.")}
          </AlertDescription>
        </Alert>
      )}

      {/* Library table */}
      {data && data.models.length > 0 && (
        <LibraryTable models={data.models} onDelete={handleDeleteClick} />
      )}

      {/* Empty state */}
      {data && data.models.length === 0 && (
        <EmptyState
          icon={HardDrive}
          title="No models downloaded"
          description="Search and download models to get started. Downloaded models will appear here."
          action={{ label: "Search Models", href: "/models/search" }}
        />
      )}

      {/* Delete confirmation dialog */}
      <DeleteModelDialog
        model={deleteTarget}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={handleDeleteConfirm}
        isDeleting={deleteModel.isPending}
      />
    </div>
  );
}
