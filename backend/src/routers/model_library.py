"""Router for managing locally downloaded models (list and delete)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from src.config import MODELS_CACHE_DIR
from src.database import ModelRepository
from src.exceptions import DeletionError, NotFoundError
from src.models.schemas import (
    DeleteResponse,
    DownloadedModel,
    ModelLibraryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_model_repo(request: Request) -> ModelRepository:
    return request.app.state.model_repo


@router.get("/library", response_model=ModelLibraryResponse)
async def list_downloaded_models(
    model_repo: ModelRepository = Depends(_get_model_repo),
):
    """List all downloaded models with disk-existence verification.

    Each model includes a ``file_exists`` flag indicating whether the
    file is still present on disk.
    """
    rows = await model_repo.get_all_downloaded_models()

    models = []
    total_size = 0
    for row in rows:
        file_exists = Path(row["file_path"]).exists()
        models.append(
            DownloadedModel(
                id=row["id"],
                repo_id=row["repo_id"],
                filename=row["filename"],
                file_path=row["file_path"],
                file_size=row["file_size"],
                download_date=row["download_date"],
                repo_author=row.get("repo_author"),
                repo_name=row.get("repo_name"),
                quantization=row.get("quantization"),
                file_exists=file_exists,
            )
        )
        if file_exists:
            total_size += row["file_size"]

    return ModelLibraryResponse(models=models, total_size=total_size)


@router.delete("/library/{model_id}", response_model=DeleteResponse)
async def delete_model(
    model_id: int,
    model_repo: ModelRepository = Depends(_get_model_repo),
):
    """Delete a downloaded model from disk and database.

    If the file is already missing from disk, the database record is
    still removed and a success response is returned with
    ``file_deleted=False``.
    """
    row = await model_repo.get_downloaded_model(model_id)
    if row is None:
        raise NotFoundError(
            f"Downloaded model with id {model_id} not found",
            detail={"model_id": model_id},
        )

    file_path = Path(row["file_path"])
    file_deleted = False

    if file_path.exists():
        try:
            os.remove(file_path)
            file_deleted = True
            logger.info("Deleted model file: %s", file_path)

            # Clean up empty parent directories up to the cache root
            _cleanup_empty_parents(file_path.parent, MODELS_CACHE_DIR)

        except PermissionError as exc:
            raise DeletionError(
                f"Cannot delete '{file_path}' — file may be in use by another process",
                detail={"file_path": str(file_path), "error": str(exc)},
            ) from exc
        except OSError as exc:
            raise DeletionError(
                f"Failed to delete '{file_path}': {exc}",
                detail={"file_path": str(file_path), "error": str(exc)},
            ) from exc
    else:
        logger.warning("Model file already missing: %s", file_path)

    db_deleted = await model_repo.delete_downloaded_model(model_id)

    return DeleteResponse(
        id=row["id"],
        repo_id=row["repo_id"],
        filename=row["filename"],
        file_deleted=file_deleted,
        db_deleted=db_deleted,
        message="Model deleted successfully" if file_deleted else "Database record removed (file was already missing)",
    )


def _cleanup_empty_parents(directory: Path, stop_at: Path) -> None:
    """Remove empty directories walking up from *directory* to *stop_at*.

    Stops as soon as a non-empty directory is found or *stop_at* is reached.
    Silently ignores errors (e.g. permissions).
    """
    try:
        stop_at = stop_at.resolve()
        current = directory.resolve()
        while current != stop_at and current.is_dir():
            if any(current.iterdir()):
                break  # directory is not empty
            shutil.rmtree(current, ignore_errors=True)
            current = current.parent
    except Exception:
        pass  # best-effort cleanup
