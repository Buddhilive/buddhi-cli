"""Application configuration and path constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
MODELS_CACHE_DIR = Path(os.getenv("MODELS_CACHE_DIR", str(BACKEND_DIR / "models")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "buddhi.db")))

# HuggingFace settings
HF_TOKEN: str | None = os.getenv("HF_TOKEN", None)

# Download settings
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))

# Search defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
