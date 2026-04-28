"""Collect Claude stream-json events into portal assistant message blocks."""
from __future__ import annotations

import json
import uuid
from typing import Any


class AssistantBlockCollector:
    """Accumulate the assistant turn in the same block order the UI streams."""

    def __init__(self) -> None:
        self.blocks: list[dict[str, Any]] = []
        self._current_tool_id: str | None = None
        self._tool_input_buffers: dict[str, str] = {}

    def ingest(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "stream_event":
            self._ingest_stream_event(event.get("event"))
        elif event_type == "user":
            self._ingest_user_message(event.get("message"))
        elif event_type == "assistant" and not self.blocks:
            self._ingest_assistant_message(event.get("message"))

    def has_blocks(self) -> bool:
        return bool(self.blocks)

    def text_content(self) -> str:
        return "".join(
            block.get("text", "")
            for block in self.blocks
            if block.get("kind") == "text" and isinstance(block.get("text"), str)
        )

    def _ingest_stream_event(self, event: Any) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "content_block_start":
            self._start_content_block(event.get("content_block"))
        elif event_type == "content_block_delta":
            self._append_delta(event.get("delta"))

    def _start_content_block(self, content_block: Any) -> None:
        if not isinstance(content_block, dict):
            return
        block_type = content_block.get("type")
        if block_type == "text":
            self.blocks.append({"kind": "text", "text": ""})
        elif block_type == "thinking":
            self.blocks.append({"kind": "thinking", "text": ""})
        elif block_type == "tool_use":
            tool_id = (
                content_block.get("id")
                if isinstance(content_block.get("id"), str)
                else f"tool-{uuid.uuid4()}"
            )
            self._current_tool_id = tool_id
            self._tool_input_buffers[tool_id] = ""
            self.blocks.append({
                "kind": "tool_use",
                "id": tool_id,
                "name": content_block.get("name")
                if isinstance(content_block.get("name"), str)
                else "tool",
                "input": content_block.get("input")
                if isinstance(content_block.get("input"), dict)
                else {},
                "isStreaming": True,
            })

    def _append_delta(self, delta: Any) -> None:
        if not isinstance(delta, dict):
            return
        delta_type = delta.get("type")
        if delta_type == "text_delta" and isinstance(delta.get("text"), str):
            self._append_text("text", delta["text"])
        elif delta_type == "thinking_delta":
            thinking = delta.get("text") or delta.get("thinking")
            if isinstance(thinking, str):
                self._append_text("thinking", thinking)
        elif (
            delta_type == "input_json_delta"
            and isinstance(delta.get("partial_json"), str)
            and self._current_tool_id
        ):
            self._tool_input_buffers[self._current_tool_id] += delta["partial_json"]

    def _append_text(self, kind: str, text: str) -> None:
        last = self.blocks[-1] if self.blocks else None
        if isinstance(last, dict) and last.get("kind") == kind:
            last["text"] = str(last.get("text", "")) + text
        else:
            self.blocks.append({"kind": kind, "text": text})

    def _ingest_user_message(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        content = message.get("content")
        if not isinstance(content, list):
            return
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                self._finalize_tool_result(block)

    def _finalize_tool_result(self, block: dict[str, Any]) -> None:
        tool_use_id = block.get("tool_use_id")
        if not isinstance(tool_use_id, str):
            return
        parsed_input = self._parse_tool_input(
            self._tool_input_buffers.pop(tool_use_id, ""),
        )
        output = self._tool_result_output(block)
        error = output if block.get("is_error") else None

        for existing in self.blocks:
            if existing.get("kind") == "tool_use" and existing.get("id") == tool_use_id:
                if parsed_input is not None:
                    existing["input"] = parsed_input
                existing["output"] = output
                existing["error"] = error
                existing["isStreaming"] = False
                if self._current_tool_id == tool_use_id:
                    self._current_tool_id = None
                return

        self.blocks.append({
            "kind": "tool_use",
            "id": tool_use_id,
            "name": "tool",
            "input": parsed_input or {},
            "output": output,
            "error": error,
            "isStreaming": False,
        })

    def _ingest_assistant_message(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        content = message.get("content")
        if isinstance(content, str):
            self.blocks.append({"kind": "text", "text": content})
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    self.blocks.append({"kind": "text", "text": block["text"]})
                elif block.get("type") == "thinking" and isinstance(block.get("text"), str):
                    self.blocks.append({"kind": "thinking", "text": block["text"]})

    @staticmethod
    def _parse_tool_input(raw: str) -> dict[str, Any] | None:
        if not raw.strip():
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
        return parsed if isinstance(parsed, dict) else {"raw": raw}

    @staticmethod
    def _tool_result_output(block: dict[str, Any]) -> str:
        raw = block.get("output", block.get("content", ""))
        if isinstance(raw, list):
            return "".join(
                item.get("text", "")
                for item in raw
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
        return str(raw)
