"""A standalone Python script that impersonates `claude -p --output-format stream-json`.

Behavior controlled by env vars (set by tests):
- MOCK_CLAUDE_MODE: 'success' (default), 'resume_fail', 'hang', 'crash', 'rate_limit'
- MOCK_CLAUDE_DELAY_MS: per-event delay (default 0)
- MOCK_CLAUDE_PROMPT_FILE: optional file to echo back as 'thought about: <prompt>'

Run as: python mock_claude.py -p '<prompt>' --session-id <uuid> ...
or:    python mock_claude.py -p '<prompt>' --resume <uuid> ...
"""
import argparse
import json
import os
import sys
import time
import uuid


def emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()
    delay_ms = int(os.environ.get("MOCK_CLAUDE_DELAY_MS", "0"))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", dest="prompt", required=True)
    parser.add_argument("--session-id", dest="session_id")
    parser.add_argument("--resume", dest="resume")
    parser.add_argument("--output-format", default="stream-json")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--include-partial-messages", action="store_true")
    args = parser.parse_args()

    mode = os.environ.get("MOCK_CLAUDE_MODE", "success")

    # Modes that fail before producing any normal output
    if mode == "resume_fail" and args.resume:
        emit({"type": "system", "subtype": "error",
              "error": "session not found", "is_error": True})
        return 1
    if mode == "crash":
        sys.stderr.write("fatal: simulated crash\n")
        return 137
    if mode == "hang":
        time.sleep(600)  # block forever; test should kill us
        return 0
    if mode == "rate_limit":
        emit({"type": "system", "subtype": "api_retry",
              "wait_seconds": 45})
        emit({"type": "system", "subtype": "init",
              "session_id": args.session_id or args.resume or str(uuid.uuid4())})
        emit({"type": "assistant", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "ok after retry"}],
        }})
        emit({"type": "result", "cost_usd": 0.001, "duration_ms": 200,
              "session_id": args.session_id or args.resume})
        return 0

    # Success path
    sid = args.session_id or args.resume or str(uuid.uuid4())
    emit({"type": "system", "subtype": "init", "session_id": sid})
    emit({"type": "stream_event",
          "event": {"type": "message_start"}})
    emit({"type": "stream_event",
          "event": {"type": "content_block_start",
                    "content_block": {"type": "text"}}})
    emit({"type": "stream_event",
          "event": {"type": "content_block_delta",
                    "delta": {"type": "text_delta",
                              "text": f"thought about: {args.prompt}"}}})
    emit({"type": "stream_event",
          "event": {"type": "content_block_stop"}})
    emit({"type": "stream_event",
          "event": {"type": "message_stop"}})
    emit({"type": "assistant", "message": {
        "role": "assistant",
        "content": [{"type": "text", "text": f"thought about: {args.prompt}"}],
    }})
    emit({"type": "result", "cost_usd": 0.001, "duration_ms": 50,
          "session_id": sid})
    return 0


if __name__ == "__main__":
    sys.exit(main())
