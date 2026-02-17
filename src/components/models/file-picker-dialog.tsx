"use client";

import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useRepoFiles } from "@/hooks/use-repo-files";
import { useStartDownload } from "@/hooks/use-download-actions";
import { formatBytes } from "@/lib/format";
import { getErrorMessage } from "@/lib/api-client";

interface FilePickerDialogProps {
  repoId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog that lists GGUF files in a repo and lets the user pick one to download.
 * Files are fetched lazily when the dialog opens.
 */
export function FilePickerDialog({ repoId, open, onOpenChange }: FilePickerDialogProps) {
  const { data, isLoading, isError, error } = useRepoFiles(repoId, open);
  const startDownload = useStartDownload();

  /** Initiate a download for the selected file. */
  const handleDownload = (filename: string) => {
    startDownload.mutate(
      { repo_id: repoId, filename },
      {
        onSuccess: (res) => {
          toast.success(res.message);
          onOpenChange(false);
        },
        onError: (err) => {
          toast.error(getErrorMessage(err, "Failed to start download"));
        },
      }
    );
  };

  // Extract quantization label from filename (e.g., "Q4_K_M" from "model.Q4_K_M.gguf")
  const getQuantLabel = (filename: string): string | null => {
    const match = filename.match(/[._-]((?:I|B|)Q\d[A-Za-z0-9_]*)\./i);
    return match ? match[1] : null;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Select File to Download</DialogTitle>
          <DialogDescription className="truncate">{repoId}</DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[400px] pr-3">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between py-2">
                  <div className="space-y-1.5 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/4" />
                  </div>
                  <Skeleton className="h-8 w-20 ml-3" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <p className="text-sm text-destructive py-4">
              {getErrorMessage(error, "Failed to load files")}
            </p>
          )}

          {data && data.files.length === 0 && (
            <p className="text-sm text-muted-foreground py-4">
              No GGUF files found in this repository.
            </p>
          )}

          {data && data.files.length > 0 && (
            <div className="divide-y">
              {data.files.map((file) => {
                const quant = getQuantLabel(file.filename);
                return (
                  <div
                    key={file.filename}
                    className="flex items-center justify-between py-3 gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">
                        {file.filename}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-muted-foreground">
                          {formatBytes(file.size)}
                        </span>
                        {quant && (
                          <Badge variant="outline" className="text-xs py-0">
                            {quant}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDownload(file.filename)}
                      disabled={startDownload.isPending}
                    >
                      {startDownload.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
