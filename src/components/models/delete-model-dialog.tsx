"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatBytes } from "@/lib/format";
import type { DownloadedModel } from "@/types/models";

interface DeleteModelDialogProps {
  model: DownloadedModel | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (modelId: number) => void;
  isDeleting: boolean;
}

/** Confirmation dialog before deleting a downloaded model. */
export function DeleteModelDialog({
  model,
  open,
  onOpenChange,
  onConfirm,
  isDeleting,
}: DeleteModelDialogProps) {
  if (!model) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete Model</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this model? This will remove the file
            from disk and cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border p-3 text-sm space-y-1">
          <p className="font-medium truncate">{model.filename}</p>
          <p className="text-muted-foreground">{model.repo_id}</p>
          <p className="text-muted-foreground">{formatBytes(model.file_size)}</p>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(model.id)}
            disabled={isDeleting}
          >
            {isDeleting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
