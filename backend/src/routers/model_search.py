"""Router for searching GGUF models on HuggingFace and listing repo files."""

import asyncio

from fastapi import APIRouter, Depends, Query, Request

from src.models.schemas import (
    ModelSearchResponse,
    ModelSearchResult,
    RepoFileInfo,
    RepoFilesResponse,
)
from src.services.huggingface_service import HuggingFaceService

router = APIRouter()


def _get_hf_service(request: Request) -> HuggingFaceService:
    return request.app.state.hf_service


@router.get("/search", response_model=ModelSearchResponse)
async def search_models(
    query: str = Query(default="", description="Free-text search term"),
    author: str | None = Query(default=None, description="Filter by author/organization"),
    sort: str = Query(default="downloads", description="Sort by: downloads, likes, last_modified, created"),
    direction: int = Query(default=-1, description="-1 for descending, 1 for ascending"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    hf_service: HuggingFaceService = Depends(_get_hf_service),
):
    """Search HuggingFace for GGUF models with pagination and sorting."""
    results, has_more = await asyncio.to_thread(
        hf_service.search_gguf_models,
        query=query,
        author=author,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )

    return ModelSearchResponse(
        models=[ModelSearchResult(**m) for m in results],
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{repo_id:path}/files", response_model=RepoFilesResponse)
async def list_repo_files(
    repo_id: str,
    hf_service: HuggingFaceService = Depends(_get_hf_service),
):
    """List all GGUF files available in a HuggingFace repository.

    Useful for inspecting which quantization variants are available
    before downloading.
    """
    files = await asyncio.to_thread(hf_service.list_repo_gguf_files, repo_id)

    return RepoFilesResponse(
        repo_id=repo_id,
        files=[RepoFileInfo(**f) for f in files],
    )
