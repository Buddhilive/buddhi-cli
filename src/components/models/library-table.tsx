"use client";

import { AlertTriangle, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatBytes, formatDate } from "@/lib/format";
import type { DownloadedModel } from "@/types/models";

interface LibraryTableProps {
  models: DownloadedModel[];
  onDelete: (model: DownloadedModel) => void;
}

/** Table of downloaded models with file status and delete action. */
export function LibraryTable({ models, onDelete }: LibraryTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Model</TableHead>
            <TableHead className="hidden sm:table-cell">Quantization</TableHead>
            <TableHead className="hidden md:table-cell">Size</TableHead>
            <TableHead className="hidden lg:table-cell">Downloaded</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[50px]" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => (
            <TableRow key={model.id}>
              <TableCell>
                <div className="min-w-0">
                  <p className="font-medium text-sm truncate max-w-[200px] lg:max-w-[300px]">
                    {model.repo_name || model.filename}
                  </p>
                  <p className="text-xs text-muted-foreground truncate max-w-[200px] lg:max-w-[300px]">
                    {model.repo_author && `${model.repo_author} / `}
                    {model.filename}
                  </p>
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                {model.quantization ? (
                  <Badge variant="outline" className="text-xs">
                    {model.quantization}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell className="hidden md:table-cell text-sm">
                {formatBytes(model.file_size)}
              </TableCell>
              <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                {formatDate(model.download_date)}
              </TableCell>
              <TableCell>
                {model.file_exists ? (
                  <Badge
                    variant="outline"
                    className="text-xs text-green-600 border-green-600/30"
                  >
                    Ready
                  </Badge>
                ) : (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Badge variant="destructive" className="text-xs gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Missing
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent>
                      File not found on disk
                    </TooltipContent>
                  </Tooltip>
                )}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => onDelete(model)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
