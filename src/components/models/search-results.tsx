"use client";

import { ModelCard } from "@/components/models/model-card";
import type { ModelSearchResult } from "@/types/models";

interface SearchResultsProps {
  models: ModelSearchResult[];
  onDownload: (repoId: string) => void;
}

/** Grid of model cards for search results. */
export function SearchResults({ models, onDownload }: SearchResultsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {models.map((model) => (
        <ModelCard key={model.id} model={model} onDownload={onDownload} />
      ))}
    </div>
  );
}
