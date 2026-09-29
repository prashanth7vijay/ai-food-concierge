"""
Structured JSON logging with contextual IDs (request_id, conversation_id,
agent_run_id) so a single user interaction can be traced end-to-end:

    HTTP request -> agent run -> LLM call -> tool call -> DB query -> response

We deliberately avoid logging full LLM prompts/responses or raw user PII;
only sizes, latencies, outcomes, and truncated previews are logged.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from typing import Any

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
conversation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "conversation_id", default=None
)
agent_run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "agent_run_id", default=None
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "conversation_id": conversation_id_var.get(),
            "agent_run_id": agent_run_id_var.get(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """Log with structured extra fields, e.g.:
    log_event(logger, logging.INFO, "tool_call_completed",
              tool_name="search_food", latency_ms=42, result_count=5)
    """
    logger.log(level, message, extra={"extra_fields": fields})
