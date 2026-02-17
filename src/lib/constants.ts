/** Base URL for the Next.js API proxy (relative, same origin). */
export const API_BASE = "/api/models";

export const DEFAULT_PAGE_SIZE = 20;

export const SORT_OPTIONS = [
  { value: "downloads", label: "Most Downloads" },
  { value: "likes", label: "Most Likes" },
  { value: "last_modified", label: "Recently Updated" },
  { value: "created", label: "Newest" },
] as const;
