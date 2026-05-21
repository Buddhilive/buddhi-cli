from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path

# Resolve base dir
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application settings, populated via environment variables.
    """
    app_name: str = "LiteRT-LM Responses API"
    model_path: str = Field(
        default=str(BASE_DIR / "server" / "static" / "model" / "gemma-4-E4B-it.litertlm"),
        description="Path to the LiteRT-LM model file."
    )

    host: str = Field(
        default="127.0.0.1",
        description="The host bind address for the backend server."
    )
    port: int = Field(
        default=58421,
        description="The port on which the backend server runs."
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
