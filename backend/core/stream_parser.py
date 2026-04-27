"""Line-buffered parser for `claude -p --output-format stream-json` output.

Anthropic stream-json events observed from Claude Code 2.1.119:
- system: common subtypes include init, retry, rate_limit, billing_error,
          status, hook_started, hook_response, and error; subtype is open-ended.
- stream_event: wraps message_start, content_block_start,
                content_block_delta, content_block_stop, message_delta,
                and message_stop events.
- assistant: full assembled assistant message.
- user: tool_result echo.
- rate_limit_event: top-level rate-limit envelope.
- result: final session envelope with duration, final assistant text, cost, and usage.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any, Literal, TypedDict


logger = logging.getLogger(__name__)


class StreamJsonEvent(TypedDict, total=False):
    """Loose shape for Claude Code stream-json events.

    `total=False` intentionally allows partial events in tests and callers. Claude
    may add fields over time, so this captures the known surface without trying
    to be an exhaustive closed schema.
    """

    type: Literal["system", "stream_event", "assistant", "user", "result", "rate_limit_event"]
    subtype: str

    # Common envelope fields
    session_id: str
    uuid: str
    parent_tool_use_id: str | None

    # system envelopes
    cwd: str
    tools: list[str]
    mcp_servers: list[dict[str, Any]]
    model: str
    permissionMode: str
    slash_commands: list[str]
    apiKeySource: str
    claude_code_version: str
    output_style: str
    agents: list[str]
    skills: list[str]
    plugins: list[dict[str, Any]]
    analytics_disabled: bool
    memory_paths: dict[str, Any]
    fast_mode_state: str
    status: str
    hook_id: str
    hook_name: str
    hook_event: str
    output: str
    stdout: str
    stderr: str
    exit_code: int
    outcome: str

    # stream_event / assistant / user payloads
    event: dict[str, Any]
    message: dict[str, Any]
    content: str
    content_block: dict[str, Any]
    delta: dict[str, Any]
    ttft_ms: int

    # rate_limit_event payloads
    rate_limit_info: dict[str, Any]
    wait_seconds: int

    # result envelope
    is_error: bool
    api_error_status: str | None
    duration_ms: int
    duration_api_ms: int
    num_turns: int
    result: str
    stop_reason: str
    total_cost_usd: float
    usage: dict[str, Any]
    modelUsage: dict[str, Any]
    permission_denials: list[Any]
    terminal_reason: str


def is_terminal(event: StreamJsonEvent) -> bool:
    """Return True if this event signals the end of a turn."""
    return event.get("type") == "result"


class LineBufferedParser:
    """Parse NDJSON from `claude -p` while preserving partial lines.

    Chunks from a subprocess pipe or HTTP stream can split a JSON object across
    arbitrary boundaries, so incomplete lines stay buffered until a newline or EOF.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> Iterator[StreamJsonEvent]:
        """Append a chunk and yield all complete events currently available."""
        if not chunk:
            return

        self._buffer.extend(chunk)
        while True:
            newline_idx = self._buffer.find(b"\n")
            if newline_idx == -1:
                return

            line = bytes(self._buffer[:newline_idx])
            del self._buffer[: newline_idx + 1]

            event = self._parse_line(line)
            if event is not None:
                yield event

    def eof(self) -> Iterator[StreamJsonEvent]:
        """Flush any buffered partial line after the stream closes."""
        if not self._buffer:
            return

        line = bytes(self._buffer)
        self._buffer.clear()

        event = self._parse_eof_line(line)
        if event is not None:
            yield event

    def _parse_eof_line(self, line: bytes) -> StreamJsonEvent | None:
        """Parse the final unterminated line, with EOF-only object-close repair."""
        if not line.strip():
            return None

        try:
            return json.loads(line.decode("utf-8"))
        except UnicodeDecodeError as exc:
            logger.warning(
                "stream_parser: malformed line dropped (len=%d): %s",
                len(line),
                exc,
            )
            return None
        except json.JSONDecodeError as exc:
            repaired = self._repair_missing_object_close(line)
            if repaired is not None:
                try:
                    return json.loads(repaired.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            logger.warning(
                "stream_parser: malformed line dropped (len=%d): %s",
                len(line),
                exc,
            )
            return None

    def _parse_line(self, line: bytes) -> StreamJsonEvent | None:
        """Parse one JSON line, logging and dropping malformed input."""
        if not line.strip():
            return None

        try:
            return json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning(
                "stream_parser: malformed line dropped (len=%d): %s",
                len(line),
                exc,
            )
            return None

    def _repair_missing_object_close(self, line: bytes) -> bytes | None:
        """Repair one missing trailing `}` for EOF partial-line compatibility."""
        stripped = line.rstrip()
        if (
            stripped.startswith(b"{")
            and not stripped.endswith(b"}")
            and stripped.count(b"{") == stripped.count(b"}") + 1
        ):
            return stripped + b"}"
        return None
