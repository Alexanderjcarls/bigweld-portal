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

from typing import Any, Literal, TypedDict


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
