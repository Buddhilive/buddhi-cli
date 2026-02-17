"""Pydantic request/response schemas for the Model Management API."""

from pydantic import BaseModel, Field


# ──────────────────────────── Search ────────────────────────────


class ModelSearchResult(BaseModel):
    """A single model returned from HuggingFace search."""

    id: str = Field(description="Full repo ID, e.g. 'TheBloke/Llama-2-7B-GGUF'")
    author: str | None = None
    model_name: str = Field(description="Repository name without author prefix")
    tags: list[str] = []
    downloads: int = 0
    likes: int = 0
    last_modified: str | None = None
    pipeline_tag: str | None = None


class ModelSearchResponse(BaseModel):
    models: list[ModelSearchResult]
    page: int
    page_size: int
    has_more: bool


# ──────────────────────── Repo Files ────────────────────────────


class RepoFileInfo(BaseModel):
    """A single GGUF file within a HuggingFace repository."""

    filename: str
    size: int = Field(description="File size in bytes")


class RepoFilesResponse(BaseModel):
    repo_id: str
    files: list[RepoFileInfo]


# ─────────────────────── Download ───────────────────────────────


class DownloadRequest(BaseModel):
    repo_id: str = Field(description="HuggingFace repo ID, e.g. 'TheBloke/Llama-2-7B-GGUF'")
    filename: str = Field(description="GGUF filename to download, e.g. 'llama-2-7b.Q4_K_M.gguf'")


class DownloadStartResponse(BaseModel):
    download_id: str
    status: str
    message: str


class DownloadProgress(BaseModel):
    download_id: str
    repo_id: str
    filename: str
    status: str = Field(description="pending | downloading | completed | failed | cancelled")
    progress: float = Field(description="0.0 to 100.0")
    downloaded_bytes: int = 0
    total_bytes: int = 0
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class DownloadListResponse(BaseModel):
    downloads: list[DownloadProgress]


class CancelResponse(BaseModel):
    download_id: str
    status: str
    message: str


# ──────────────────────── Library ───────────────────────────────


class DownloadedModel(BaseModel):
    """A model that has been downloaded and stored locally."""

    id: int
    repo_id: str
    filename: str
    file_path: str
    file_size: int = Field(description="Size in bytes")
    download_date: str
    repo_author: str | None = None
    repo_name: str | None = None
    quantization: str | None = None
    file_exists: bool = Field(description="Whether the file still exists on disk")


class ModelLibraryResponse(BaseModel):
    models: list[DownloadedModel]
    total_size: int = Field(description="Sum of all file sizes in bytes")


class DeleteResponse(BaseModel):
    id: int
    repo_id: str
    filename: str
    file_deleted: bool
    db_deleted: bool
    message: str


# ──────────────────────── Errors ────────────────────────────────


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: str | dict | None = None
