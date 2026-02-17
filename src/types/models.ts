// ────────────────────────── Search ──────────────────────────

/** A single model from HuggingFace search results. */
export interface ModelSearchResult {
  id: string;
  author: string | null;
  model_name: string;
  tags: string[];
  downloads: number;
  likes: number;
  last_modified: string | null;
  pipeline_tag: string | null;
}

export interface ModelSearchResponse {
  models: ModelSearchResult[];
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface SearchParams {
  query: string;
  author?: string;
  sort: "downloads" | "likes" | "last_modified" | "created";
  direction: -1 | 1;
  page: number;
  page_size: number;
}

// ────────────────────── Repo Files ──────────────────────────

export interface RepoFileInfo {
  filename: string;
  size: number;
}

export interface RepoFilesResponse {
  repo_id: string;
  files: RepoFileInfo[];
}

// ──────────────────── Downloads ─────────────────────────────

export interface DownloadRequest {
  repo_id: string;
  filename: string;
}

export interface DownloadStartResponse {
  download_id: string;
  status: string;
  message: string;
}

export type DownloadStatus =
  | "pending"
  | "downloading"
  | "completed"
  | "failed"
  | "cancelled";

export interface DownloadProgress {
  download_id: string;
  repo_id: string;
  filename: string;
  status: DownloadStatus;
  progress: number;
  downloaded_bytes: number;
  total_bytes: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  file_path?: string;
}

export interface DownloadListResponse {
  downloads: DownloadProgress[];
}

export interface CancelResponse {
  download_id: string;
  status: string;
  message: string;
}

// ──────────────────── SSE Events ────────────────────────────

/** The event types emitted by the SSE progress endpoint. */
export type SSEEventType =
  | "progress"
  | "downloading"
  | "completed"
  | "failed"
  | "cancelled"
  | "error";

// ────────────────────── Library ─────────────────────────────

export interface DownloadedModel {
  id: number;
  repo_id: string;
  filename: string;
  file_path: string;
  file_size: number;
  download_date: string;
  repo_author: string | null;
  repo_name: string | null;
  quantization: string | null;
  file_exists: boolean;
}

export interface ModelLibraryResponse {
  models: DownloadedModel[];
  total_size: number;
}

export interface DeleteResponse {
  id: number;
  repo_id: string;
  filename: string;
  file_deleted: boolean;
  db_deleted: boolean;
  message: string;
}

// ────────────────────── Errors ──────────────────────────────

export interface APIError {
  error: string;
  message: string;
  detail?: string | Record<string, unknown> | null;
}
