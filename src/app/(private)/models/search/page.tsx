"use client";

import { useState, useEffect } from "react";
import { AlertCircle, SearchIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SearchBar } from "@/components/models/search-bar";
import { SearchResults } from "@/components/models/search-results";
import { FilePickerDialog } from "@/components/models/file-picker-dialog";
import { EmptyState } from "@/components/models/empty-state";
import { useModelSearch } from "@/hooks/use-model-search";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants";
import { getErrorMessage } from "@/lib/api-client";
import type { SearchParams } from "@/types/models";

export default function ModelSearchPage() {
  const [inputValue, setInputValue] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [sort, setSort] = useState<SearchParams["sort"]>("downloads");
  const [page, setPage] = useState(1);

  // File picker dialog state
  const [pickerRepoId, setPickerRepoId] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(inputValue);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [inputValue]);

  const { data, isLoading, isError, error, isFetching } = useModelSearch({
    query: debouncedQuery,
    sort,
    direction: -1,
    page,
    page_size: DEFAULT_PAGE_SIZE,
  });

  /** Open the file picker dialog for a given repo. */
  const handleDownloadClick = (repoId: string) => {
    setPickerRepoId(repoId);
    setPickerOpen(true);
  };

  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search Models</h1>
        <p className="text-sm text-muted-foreground">
          Search for GGUF models on HuggingFace
        </p>
      </div>

      <SearchBar
        query={inputValue}
        onQueryChange={setInputValue}
        sort={sort}
        onSortChange={(v) => {
          setSort(v as SearchParams["sort"]);
          setPage(1);
        }}
      />

      {/* Initial state — no query yet */}
      {!debouncedQuery && (
        <EmptyState
          icon={SearchIcon}
          title="Search for models"
          description="Enter a search term above to find GGUF models on HuggingFace."
        />
      )}

      {/* Loading skeletons */}
      {debouncedQuery && isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border p-4 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-8 w-full" />
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
            {getErrorMessage(error, "Failed to search models. Please try again.")}
          </AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {data && data.models.length > 0 && (
        <>
          <SearchResults models={data.models} onDownload={handleDownloadClick} />

          {/* Pagination */}
          <div className="flex items-center justify-between pt-2">
            <p className="text-sm text-muted-foreground">
              Page {data.page}
              {isFetching && " ..."}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.has_more}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      {/* No results */}
      {data && data.models.length === 0 && debouncedQuery && (
        <EmptyState
          icon={SearchIcon}
          title="No models found"
          description={`No GGUF models match "${debouncedQuery}". Try a different search term.`}
        />
      )}

      {/* File picker dialog */}
      {pickerRepoId && (
        <FilePickerDialog
          repoId={pickerRepoId}
          open={pickerOpen}
          onOpenChange={setPickerOpen}
        />
      )}
    </div>
  );
}
