"use client";

import { Download, Heart, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCompact, formatDate } from "@/lib/format";
import type { ModelSearchResult } from "@/types/models";

interface ModelCardProps {
  model: ModelSearchResult;
  onDownload: (repoId: string) => void;
}

/** Card displaying a single search result with model info and download action. */
export function ModelCard({ model, onDownload }: ModelCardProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-base leading-tight line-clamp-1">
          {model.model_name}
        </CardTitle>
        {model.author && (
          <p className="text-sm text-muted-foreground">{model.author}</p>
        )}
      </CardHeader>

      <CardContent className="flex-1 space-y-3">
        {/* Tags */}
        {model.pipeline_tag && (
          <Badge variant="secondary" className="text-xs">
            {model.pipeline_tag}
          </Badge>
        )}

        {/* Stats row */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Download className="h-3.5 w-3.5" />
            {formatCompact(model.downloads)}
          </span>
          <span className="flex items-center gap-1">
            <Heart className="h-3.5 w-3.5" />
            {formatCompact(model.likes)}
          </span>
          {model.last_modified && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDate(model.last_modified)}
            </span>
          )}
        </div>
      </CardContent>

      <CardFooter className="pt-0">
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onDownload(model.id)}
        >
          <Download className="h-4 w-4 mr-2" />
          Download
        </Button>
      </CardFooter>
    </Card>
  );
}
