"""Custom exception hierarchy for the BuddhiAI API."""


class BuddhiAPIError(Exception):
    """Base exception for all API errors. Caught by the global exception handler."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        detail: str | dict | None = None,
    ):
        self.status_code = status_code
        self.error = error
        self.message = message
        self.detail = detail
        super().__init__(message)


class UpstreamError(BuddhiAPIError):
    """HuggingFace API or other upstream service failure (502)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(502, "upstream_error", message, detail)


class HFNotFoundError(BuddhiAPIError):
    """Repository or file not found on HuggingFace (404)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(404, "hf_not_found", message, detail)


class NotFoundError(BuddhiAPIError):
    """Local resource not found (404)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(404, "not_found", message, detail)


class DownloadConflictError(BuddhiAPIError):
    """Download already in progress or file already exists (409)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(409, "download_conflict", message, detail)


class DatabaseError(BuddhiAPIError):
    """Database operation failed (500)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(500, "database_error", message, detail)


class DeletionError(BuddhiAPIError):
    """File deletion failed, e.g. file locked by another process (500)."""

    def __init__(self, message: str, detail: str | dict | None = None):
        super().__init__(500, "deletion_failed", message, detail)


class DownloadCancelledException(Exception):
    """Raised inside the custom tqdm class to abort a download."""

    def __init__(self, download_id: str):
        self.download_id = download_id
        super().__init__(f"Download {download_id} was cancelled")
