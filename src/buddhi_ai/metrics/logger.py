import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import tiktoken

from buddhi_ai.metrics.constants import TOKEN_ENCODING
from buddhi_ai.metrics.db import init_metrics_db

logger = logging.getLogger(__name__)

class MetricsLogger:
    """Singleton for logging tool usage metrics safely to a SQLite database."""
    
    _encoder = None
    
    @classmethod
    def _get_encoder(cls):
        if cls._encoder is None:
            try:
                cls._encoder = tiktoken.get_encoding(TOKEN_ENCODING)
            except Exception:
                # Fallback if tiktoken fails
                cls._encoder = tiktoken.get_encoding("cl100k_base")
        return cls._encoder

    @classmethod
    def count_tokens(cls, text: str) -> int:
        """Count tokens in a string using the configured encoder."""
        if not text:
            return 0
        try:
            return len(cls._get_encoder().encode(text))
        except Exception:
            # Safe fallback if encoding fails: 1 token roughly = 4 chars
            return len(text) // 4

    @classmethod
    def log(
        cls,
        tool_name: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        raw_input_tokens: Optional[int] = None,
        tokens_saved: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        workspace_path: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log a tool usage event to the metrics database.
        Failures are caught and ignored to prevent crashing the main application.
        """
        try:
            now = datetime.now(timezone.utc)
            timestamp_iso = now.isoformat()
            timestamp_unix = now.timestamp()
            
            extra_json = json.dumps(extra) if extra else None

            conn = init_metrics_db()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tool_events (
                        tool_name, timestamp_iso, timestamp_unix,
                        input_tokens, output_tokens, raw_input_tokens, tokens_saved,
                        status, error_message, duration_ms, workspace_path, extra_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tool_name, timestamp_iso, timestamp_unix,
                        input_tokens, output_tokens, raw_input_tokens, tokens_saved,
                        status, error_message, duration_ms, workspace_path, extra_json
                    )
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            # Silently swallow errors to avoid crashing the tool
            logger.debug(f"Failed to log metrics for {tool_name}: {e}")
