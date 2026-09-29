from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from backend.core.logging import get_logger, log_event

logger = get_logger("tools")

T = TypeVar("T")


class ToolError(Exception):
    """Raised by a tool for any failure — invalid arguments, not-found
    records, or unexpected internal errors. Callers (the agent graph)
    always catch this and turn it into a structured, safe response;
    a ToolError is never allowed to propagate as a raw 500 with internal
    detail leaked to the user."""

    def __init__(self, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.message = message
        self.retriable = retriable  # transient vs permanent, per spec section 14


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    arguments: dict = field(default_factory=dict)


def validate_params(schema: type[BaseModel], raw_args: dict) -> BaseModel:
    """Every tool call's arguments must pass strict Pydantic validation
    before touching any business logic or the database. Guards against
    malformed parameters, negative prices, invalid enums, unsupported
    fields, etc. (spec section 13)."""
    try:
        return schema.model_validate(raw_args)
    except ValidationError as exc:
        raise ToolError(f"Invalid arguments for tool: {exc.errors()!s}") from exc


def run_tool(tool_name: str, raw_args: dict, fn: Callable[..., Any]) -> ToolResult:
    """Wraps a tool function with timing + structured logging, converting
    any exception into a ToolResult(success=False) rather than raising."""
    start = time.perf_counter()
    try:
        data = fn()
        latency_ms = (time.perf_counter() - start) * 1000
        log_event(
            logger,
            logging.INFO,
            "tool_call_completed",
            tool_name=tool_name,
            latency_ms=round(latency_ms, 2),
        )
        return ToolResult(
            tool_name=tool_name, success=True, data=data, latency_ms=latency_ms, arguments=raw_args
        )
    except ToolError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        log_event(
            logger,
            logging.WARNING,
            "tool_call_failed",
            tool_name=tool_name,
            latency_ms=round(latency_ms, 2),
            error=exc.message,
            retriable=exc.retriable,
        )
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error=exc.message,
            latency_ms=latency_ms,
            arguments=raw_args,
        )
    except Exception as exc:  # noqa: BLE001 - last line of defense, never leak raw errors
        latency_ms = (time.perf_counter() - start) * 1000
        log_event(
            logger,
            logging.ERROR,
            "tool_call_unexpected_error",
            tool_name=tool_name,
            latency_ms=round(latency_ms, 2),
            error=str(exc),
        )
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error="Internal error while executing tool.",
            latency_ms=latency_ms,
            arguments=raw_args,
        )
