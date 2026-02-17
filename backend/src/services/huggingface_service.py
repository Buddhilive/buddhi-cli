"""Wrapper around the huggingface_hub library for GGUF model operations.

All methods are synchronous (the HF library is synchronous) and should be
called from ``asyncio.to_thread()`` in async contexts to avoid blocking.
"""

from __future__ import annotations

import itertools
import logging
import re
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import (
    EntryNotFoundError,
    HfHubHTTPError,
    RepositoryNotFoundError,
)

from src.exceptions import HFNotFoundError, UpstreamError

logger = logging.getLogger(__name__)

# Regex to extract quantization level from GGUF filenames
# e.g. "llama-2-7b.Q4_K_M.gguf" → "Q4_K_M"
_QUANT_PATTERN = re.compile(r"[.\-_]((?:IQ|Q|F|BF)\d[A-Za-z0-9_]*)\.", re.IGNORECASE)


def extract_quantization(filename: str) -> str | None:
    """Extract the quantization identifier from a GGUF filename."""
    match = _QUANT_PATTERN.search(filename)
    return match.group(1) if match else None


class HuggingFaceService:
    """Encapsulates all interactions with the HuggingFace Hub API."""

    def __init__(self, token: str | None = None):
        self.api = HfApi(token=token)

    # ──────────────────────── Search ────────────────────────────

    def search_gguf_models(
        self,
        query: str = "",
        author: str | None = None,
        sort: str = "downloads",
        direction: int = -1,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Search HuggingFace for GGUF models.

        Args:
            query: Free-text search term.
            author: Filter by author/organization.
            sort: Sort field – "downloads", "likes", "last_modified", "created".
            direction: -1 for descending, 1 for ascending.
            page: 1-indexed page number.
            page_size: Number of results per page.

        Returns:
            Tuple of (results_list, has_more).
        """
        try:
            kwargs: dict[str, Any] = {
                "filter": ["gguf"],
                "sort": sort,
                "direction": direction,
            }
            if query:
                kwargs["search"] = query
            if author:
                kwargs["author"] = author

            iterator = self.api.list_models(**kwargs)

            # Skip to the requested page
            offset = (page - 1) * page_size
            sliced = itertools.islice(iterator, offset, offset + page_size + 1)
            results = list(sliced)

            has_more = len(results) > page_size
            results = results[:page_size]

            return [self._model_info_to_dict(m) for m in results], has_more

        except HfHubHTTPError as exc:
            logger.error("HuggingFace search failed: %s", exc)
            raise UpstreamError(
                f"HuggingFace API error during search: {exc}",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during model search: %s", exc)
            raise UpstreamError(
                "Failed to search models on HuggingFace",
                detail=str(exc),
            ) from exc

    # ──────────────────── List repo files ───────────────────────

    def list_repo_gguf_files(self, repo_id: str) -> list[dict[str, Any]]:
        """List all .gguf files in a HuggingFace repository.

        Args:
            repo_id: Full repository ID, e.g. "TheBloke/Llama-2-7B-GGUF".

        Returns:
            List of dicts with filename and size for each GGUF file.
        """
        try:
            tree = self.api.list_repo_tree(repo_id, recursive=True)
            gguf_files = []
            for entry in tree:
                # list_repo_tree returns RepoFile and RepoFolder objects;
                # only RepoFile has a size attribute.
                if not hasattr(entry, "size"):
                    continue
                if entry.rfilename.lower().endswith(".gguf"):
                    gguf_files.append(
                        {
                            "filename": entry.rfilename,
                            "size": entry.size or 0,
                        }
                    )
            return gguf_files

        except RepositoryNotFoundError as exc:
            raise HFNotFoundError(
                f"Repository '{repo_id}' not found on HuggingFace",
                detail={"repo_id": repo_id},
            ) from exc
        except HfHubHTTPError as exc:
            logger.error("HuggingFace API error listing files: %s", exc)
            raise UpstreamError(
                f"HuggingFace API error: {exc}",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error listing repo files: %s", exc)
            raise UpstreamError(
                f"Failed to list files for '{repo_id}'",
                detail=str(exc),
            ) from exc

    # ─────────────────────── Download ───────────────────────────

    def download_file(
        self,
        repo_id: str,
        filename: str,
        cache_dir: Path,
        tqdm_class: type | None = None,
    ) -> str:
        """Download a single file from a HuggingFace repository.

        Uses hf_hub_download with a custom cache_dir so models are stored
        in a dedicated directory rather than the global HF cache.

        Args:
            repo_id: Full repository ID.
            filename: The file to download within the repo.
            cache_dir: Local directory to use as HF cache.
            tqdm_class: Optional custom tqdm class for progress tracking.

        Returns:
            Absolute path to the downloaded file.
        """
        try:
            kwargs: dict[str, Any] = {
                "repo_id": repo_id,
                "filename": filename,
                "cache_dir": str(cache_dir),
            }
            if tqdm_class is not None:
                kwargs["tqdm_class"] = tqdm_class

            file_path = hf_hub_download(**kwargs)
            return str(Path(file_path).resolve())

        except EntryNotFoundError as exc:
            raise HFNotFoundError(
                f"File '{filename}' not found in repository '{repo_id}'",
                detail={"repo_id": repo_id, "filename": filename},
            ) from exc
        except RepositoryNotFoundError as exc:
            raise HFNotFoundError(
                f"Repository '{repo_id}' not found on HuggingFace",
                detail={"repo_id": repo_id},
            ) from exc
        except HfHubHTTPError as exc:
            logger.error("HuggingFace download error: %s", exc)
            raise UpstreamError(
                f"HuggingFace download failed: {exc}",
                detail=str(exc),
            ) from exc

    # ──────────────────── Internal helpers ──────────────────────

    @staticmethod
    def _model_info_to_dict(model: Any) -> dict[str, Any]:
        """Convert a ModelInfo object to a plain dict for the response."""
        model_id: str = model.id or ""
        parts = model_id.split("/", 1)
        author = parts[0] if len(parts) > 1 else None
        model_name = parts[1] if len(parts) > 1 else parts[0]

        return {
            "id": model_id,
            "author": author,
            "model_name": model_name,
            "tags": list(model.tags or []),
            "downloads": model.downloads or 0,
            "likes": model.likes or 0,
            "last_modified": model.last_modified.isoformat() if model.last_modified else None,
            "pipeline_tag": model.pipeline_tag,
        }
