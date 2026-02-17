"""Download orchestration service with real-time progress tracking.

Manages background downloads via asyncio tasks, uses a custom tqdm subclass
to capture per-chunk progress in an in-memory dict, and coordinates with
the database for persistent state.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from src.config import MODELS_CACHE_DIR
from src.database import ModelRepository
from src.exceptions import (
    DownloadCancelledException,
    DownloadConflictError,
    NotFoundError,
)
from src.services.huggingface_service import HuggingFaceService, extract_quantization

logger = logging.getLogger(__name__)


@dataclass
class ProgressState:
    """In-memory snapshot of a download's progress, updated by the tqdm class."""

    download_id: str
    repo_id: str
    filename: str
    status: str = "pending"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    error_message: str | None = None
    started_at: str = ""
    completed_at: str | None = None
    file_path: str | None = None


class DownloadService:
    """Manages GGUF model downloads with progress tracking and cancellation."""

    def __init__(
        self,
        hf_service: HuggingFaceService,
        model_repo: ModelRepository,
        cache_dir: Path = MODELS_CACHE_DIR,
    ):
        self.hf_service = hf_service
        self.model_repo = model_repo
        self.cache_dir = cache_dir

        # In-memory state for real-time progress (polled by SSE endpoint)
        self._progress: dict[str, ProgressState] = {}
        # Cancellation flags checked by the custom tqdm class
        self._cancel_flags: dict[str, bool] = {}
        # Keep references to background tasks so they aren't garbage-collected
        self._tasks: dict[str, asyncio.Task] = {}

    # ─────────────────── Public interface ───────────────────────

    async def start_download(self, repo_id: str, filename: str) -> str:
        """Validate and initiate a model download.

        Returns:
            The download_id (UUID) for tracking progress.

        Raises:
            DownloadConflictError: If the file is already downloaded or a
                download is already in progress.
        """
        # Check if already downloaded and still on disk
        existing = await self.model_repo.find_downloaded_model(repo_id, filename)
        if existing and Path(existing["file_path"]).exists():
            raise DownloadConflictError(
                f"'{filename}' from '{repo_id}' is already downloaded",
                detail={"repo_id": repo_id, "filename": filename, "file_path": existing["file_path"]},
            )

        # Check if a download is already in progress
        active = await self.model_repo.find_active_download(repo_id, filename)
        if active:
            raise DownloadConflictError(
                f"Download already in progress for '{filename}' from '{repo_id}'",
                detail={"download_id": active["id"], "status": active["status"]},
            )

        download_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.model_repo.insert_active_download(download_id, repo_id, filename)

        self._progress[download_id] = ProgressState(
            download_id=download_id,
            repo_id=repo_id,
            filename=filename,
            status="pending",
            started_at=now,
        )
        self._cancel_flags[download_id] = False

        # Spawn background task
        task = asyncio.create_task(self._run_download(download_id, repo_id, filename))
        self._tasks[download_id] = task
        task.add_done_callback(lambda t: self._tasks.pop(download_id, None))

        return download_id

    def get_progress(self, download_id: str) -> ProgressState | None:
        """Return the current in-memory progress for a download."""
        return self._progress.get(download_id)

    async def cancel_download(self, download_id: str) -> str:
        """Request cancellation of an active download.

        Returns:
            The resulting status string.

        Raises:
            NotFoundError: If the download_id is unknown.
        """
        state = self._progress.get(download_id)
        if state is None:
            record = await self.model_repo.get_active_download(download_id)
            if record is None:
                raise NotFoundError(f"Download '{download_id}' not found")
            if record["status"] in ("completed", "failed", "cancelled"):
                return record["status"]

        if state and state.status in ("completed", "failed", "cancelled"):
            return state.status

        # Signal the tqdm class to raise DownloadCancelledException
        self._cancel_flags[download_id] = True
        return "cancelling"

    async def get_all_downloads(self) -> list[dict]:
        """Return all active download records from the database."""
        return await self.model_repo.get_all_active_downloads()

    async def shutdown(self) -> None:
        """Cancel all running downloads on application shutdown."""
        for download_id in list(self._tasks):
            self._cancel_flags[download_id] = True
        # Wait briefly for tasks to notice the flag
        if self._tasks:
            await asyncio.sleep(1)
            for task in self._tasks.values():
                task.cancel()

    # ─────────────────── Internal download logic ────────────────

    async def _run_download(
        self,
        download_id: str,
        repo_id: str,
        filename: str,
    ) -> None:
        """Execute the download in a background thread and update state."""
        state = self._progress[download_id]
        state.status = "downloading"

        await self.model_repo.update_download_status(
            download_id, status="downloading"
        )

        try:
            tqdm_cls = self._make_tqdm_class(download_id)
            file_path = await asyncio.to_thread(
                self.hf_service.download_file,
                repo_id,
                filename,
                self.cache_dir,
                tqdm_cls,
            )

            file_size = Path(file_path).stat().st_size
            now = datetime.now(timezone.utc).isoformat()

            # Parse repo parts
            parts = repo_id.split("/", 1)
            repo_author = parts[0] if len(parts) > 1 else None
            repo_name = parts[1] if len(parts) > 1 else parts[0]

            # Record in the downloaded_models table
            await self.model_repo.add_downloaded_model(
                repo_id=repo_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                repo_author=repo_author,
                repo_name=repo_name,
                quantization=extract_quantization(filename),
            )

            # Update active download status
            await self.model_repo.update_download_status(
                download_id,
                status="completed",
                progress=100.0,
                downloaded_bytes=file_size,
                total_bytes=file_size,
                completed_at=now,
            )

            # Update in-memory state
            state.status = "completed"
            state.progress = 100.0
            state.downloaded_bytes = file_size
            state.total_bytes = file_size
            state.completed_at = now
            state.file_path = file_path

            logger.info("Download completed: %s/%s → %s", repo_id, filename, file_path)

        except DownloadCancelledException:
            now = datetime.now(timezone.utc).isoformat()
            await self.model_repo.update_download_status(
                download_id,
                status="cancelled",
                progress=state.progress,
                downloaded_bytes=state.downloaded_bytes,
                total_bytes=state.total_bytes,
                completed_at=now,
            )
            state.status = "cancelled"
            state.completed_at = now
            logger.info("Download cancelled: %s/%s", repo_id, filename)

        except Exception as exc:
            now = datetime.now(timezone.utc).isoformat()
            error_msg = str(exc)
            await self.model_repo.update_download_status(
                download_id,
                status="failed",
                progress=state.progress,
                downloaded_bytes=state.downloaded_bytes,
                total_bytes=state.total_bytes,
                error_message=error_msg,
                completed_at=now,
            )
            state.status = "failed"
            state.error_message = error_msg
            state.completed_at = now
            logger.error("Download failed: %s/%s - %s", repo_id, filename, exc)

        finally:
            self._cancel_flags.pop(download_id, None)

    def _make_tqdm_class(self, download_id: str) -> type:
        """Create a tqdm subclass that captures progress for a specific download.

        The returned *class* (not instance) is passed to hf_hub_download as
        ``tqdm_class``. HF hub instantiates it internally and calls ``update()``
        on each downloaded chunk, which lets us intercept progress and check
        for cancellation.
        """
        service = self

        class _ProgressTqdm(tqdm):
            def __init__(self, *args, **kwargs):
                # Disable console output — we only care about the data
                kwargs["disable"] = False
                # Remove extra kwargs from newer HF hub backends (e.g. Xet)
                # that are not valid tqdm parameters
                kwargs.pop("name", None)
                super().__init__(*args, **kwargs)
                state = service._progress.get(download_id)
                if state and self.total:
                    state.total_bytes = int(self.total)

            def update(self, n=1):
                super().update(n)

                # Check cancellation flag
                if service._cancel_flags.get(download_id):
                    raise DownloadCancelledException(download_id)

                # Update in-memory progress
                state = service._progress.get(download_id)
                if state:
                    downloaded = int(self.n)
                    total = int(self.total) if self.total else 0
                    state.downloaded_bytes = downloaded
                    state.total_bytes = total
                    state.progress = round((downloaded / total) * 100, 1) if total > 0 else 0.0

            def close(self):
                super().close()

        return _ProgressTqdm
