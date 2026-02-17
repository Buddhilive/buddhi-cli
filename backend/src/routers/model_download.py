"""Router for downloading GGUF models with SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from src.database import ModelRepository
from src.models.schemas import (
    CancelResponse,
    DownloadListResponse,
    DownloadProgress,
    DownloadRequest,
    DownloadStartResponse,
)
from src.services.download_service import DownloadService

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_download_service(request: Request) -> DownloadService:
    return request.app.state.download_service


def _get_model_repo(request: Request) -> ModelRepository:
    return request.app.state.model_repo


@router.post("/download", response_model=DownloadStartResponse, status_code=202)
async def start_download(
    body: DownloadRequest,
    download_service: DownloadService = Depends(_get_download_service),
):
    """Start downloading a GGUF model file from HuggingFace.

    Returns a download_id that can be used to track progress via SSE
    at ``GET /download/{download_id}/progress``.
    """
    download_id = await download_service.start_download(body.repo_id, body.filename)

    return DownloadStartResponse(
        download_id=download_id,
        status="started",
        message=f"Download started for '{body.filename}' from '{body.repo_id}'",
    )


@router.get("/download/{download_id}/progress")
async def download_progress(
    download_id: str,
    download_service: DownloadService = Depends(_get_download_service),
    model_repo: ModelRepository = Depends(_get_model_repo),
):
    """Stream download progress via Server-Sent Events (SSE).

    Events emitted:
        - ``progress``: periodic updates with bytes downloaded, percentage, etc.
        - ``completed``: final event when download finishes successfully.
        - ``failed``: final event if the download errors out.
        - ``cancelled``: final event if the download was cancelled.
        - ``error``: if the download_id is unknown.
    """

    async def event_generator():
        """Yield SSE events until the download reaches a terminal state."""
        terminal_states = {"completed", "failed", "cancelled"}

        while True:
            # Check in-memory progress first (real-time)
            state = download_service.get_progress(download_id)

            if state is not None:
                data = {
                    "download_id": state.download_id,
                    "repo_id": state.repo_id,
                    "filename": state.filename,
                    "status": state.status,
                    "progress": state.progress,
                    "downloaded_bytes": state.downloaded_bytes,
                    "total_bytes": state.total_bytes,
                }

                if state.status == "completed":
                    data["file_path"] = state.file_path
                if state.error_message:
                    data["error_message"] = state.error_message

                yield {"event": state.status, "data": json.dumps(data)}

                if state.status in terminal_states:
                    return
            else:
                # Fallback to database (e.g. after server restart or SSE reconnect)
                record = await model_repo.get_active_download(download_id)
                if record is None:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": f"Download '{download_id}' not found"}),
                    }
                    return

                yield {
                    "event": record["status"],
                    "data": json.dumps({
                        "download_id": record["id"],
                        "repo_id": record["repo_id"],
                        "filename": record["filename"],
                        "status": record["status"],
                        "progress": record["progress"],
                        "downloaded_bytes": record["downloaded_bytes"],
                        "total_bytes": record["total_bytes"],
                        "error_message": record.get("error_message"),
                    }),
                }

                if record["status"] in terminal_states:
                    return

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/downloads", response_model=DownloadListResponse)
async def list_downloads(
    download_service: DownloadService = Depends(_get_download_service),
):
    """List all active and recent downloads with their current status."""
    records = await download_service.get_all_downloads()

    return DownloadListResponse(
        downloads=[
            DownloadProgress(
                download_id=r["id"],
                repo_id=r["repo_id"],
                filename=r["filename"],
                status=r["status"],
                progress=r["progress"],
                downloaded_bytes=r["downloaded_bytes"],
                total_bytes=r["total_bytes"],
                error_message=r.get("error_message"),
                started_at=r.get("started_at"),
                completed_at=r.get("completed_at"),
            )
            for r in records
        ]
    )


@router.post("/download/{download_id}/cancel", response_model=CancelResponse)
async def cancel_download(
    download_id: str,
    download_service: DownloadService = Depends(_get_download_service),
):
    """Cancel an active download.

    If the download has already completed or failed, returns the current status
    without error.
    """
    status = await download_service.cancel_download(download_id)

    messages = {
        "cancelling": "Cancellation requested — download will stop shortly",
        "completed": "Download already completed",
        "failed": "Download already failed",
        "cancelled": "Download was already cancelled",
    }

    return CancelResponse(
        download_id=download_id,
        status=status,
        message=messages.get(status, f"Download status: {status}"),
    )
