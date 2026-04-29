"""Filesystem JSON-canonical conversation persistence.

Layout:
  <root>/<YYYY-MM>/<conv-id>.json          # JSONL, hook-written, append-only
  <root>/<YYYY-MM>/<conv-id>.summary.md    # backend-written via atomic rename

Source-of-truth: <conv-id>.json. Claude's own session storage at
~/.claude/projects/.../session-<uuid>.jsonl is internal to claude; we never
read from it.

The first line of every conversation is a "meta" event we author at create():
  {"type":"meta","conv_id":"...","created_ts":"...","session_uuid":null}

After the first successful turn, the backend updates this meta with the
session_uuid so subsequent turns can --resume. (We rewrite the line in place
via a temp+rename - only the meta line; subsequent hook-written lines are
preserved.)
"""
import fcntl
import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConversationStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _month_dir(self, when: datetime | None = None) -> Path:
        when = when or datetime.now(timezone.utc)
        d = self._root / when.strftime("%Y-%m")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path_for(self, conv_id: str) -> Path:
        # Find the conversation across month dirs
        for month_dir in sorted(self._root.iterdir()):
            if not month_dir.is_dir():
                continue
            candidate = month_dir / f"{conv_id}.json"
            if candidate.exists():
                return candidate
        # Default to current month dir for a new conversation
        return self._month_dir() / f"{conv_id}.json"

    def summary_path_for(self, conv_id: str) -> Path:
        json_path = self.path_for(conv_id)
        return json_path.parent / f"{json_path.stem}.summary.md"

    def _lock_path(self, conv_id: str) -> Path:
        path = self.path_for(conv_id)
        return path.with_name(path.name + ".lock")

    def create(self) -> str:
        conv_id = str(uuid.uuid4())
        path = self._month_dir() / f"{conv_id}.json"
        meta = {
            "type": "meta",
            "conv_id": conv_id,
            "created_ts": datetime.now(timezone.utc).isoformat(),
            "session_uuid": None,
        }
        path.write_text(json.dumps(meta) + "\n")
        return conv_id

    def read_events(self, conv_id: str) -> list[dict[str, Any]]:
        path = self.path_for(conv_id)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("skip corrupt line in %s", path)
                continue
        return events

    def read_session_uuid(self, conv_id: str) -> str | None:
        for ev in self.read_events(conv_id):
            if ev.get("type") == "meta":
                return ev.get("session_uuid")
        return None

    def set_session_uuid(self, conv_id: str, session_uuid: str) -> None:
        """Rewrite ONLY the meta line; preserve all subsequent hook-written lines."""
        lock_path = self._lock_path(conv_id)
        with lock_path.open("a") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                path = self.path_for(conv_id)
                events = self.read_events(conv_id)
                rewrote = False
                for ev in events:
                    if ev.get("type") == "meta":
                        ev["session_uuid"] = session_uuid
                        rewrote = True
                        break
                if not rewrote:
                    events.insert(0, {
                        "type": "meta",
                        "conv_id": conv_id,
                        "session_uuid": session_uuid,
                        "created_ts": datetime.now(timezone.utc).isoformat(),
                    })
                # Atomic write via temp+rename
                tmp = path.with_suffix(".json.tmp")
                with tmp.open("w") as f:
                    for ev in events:
                        f.write(json.dumps(ev) + "\n")
                tmp.replace(path)
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)

    def append_event(self, conv_id: str, event: dict[str, Any]) -> None:
        """Append one JSONL event using the same flock path as the hooks."""
        lock_path = self._lock_path(conv_id)
        with lock_path.open("a") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                path = self.path_for(conv_id)
                with path.open("a") as f:
                    f.write(json.dumps(event) + "\n")
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)

    def append_assistant_blocks(
        self,
        conv_id: str,
        blocks: list[dict[str, Any]],
        content: str | None = None,
    ) -> None:
        event = {
            "type": "assistant",
            "blocks": blocks,
            "content": content if content is not None else self._blocks_text(blocks),
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "conv_id": conv_id,
        }
        self.append_event(conv_id, event)

    def append_usage(self, conv_id: str, usage: dict[str, Any]) -> None:
        event = {
            "type": "usage",
            "input_tokens": self._int_token(usage.get("input_tokens")),
            "cache_creation_input_tokens": self._int_token(
                usage.get("cache_creation_input_tokens")
            ),
            "cache_read_input_tokens": self._int_token(
                usage.get("cache_read_input_tokens")
            ),
            "output_tokens": self._int_token(usage.get("output_tokens")),
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "conv_id": conv_id,
        }
        self.append_event(conv_id, event)

    def get_max_usage_total(self, conv_id: str) -> int:
        """Return max(input + cache_creation + cache_read) across all usage events.

        Stored usage events come from Claude Code's stream-json `result` event, which
        aggregates token counts across every agentic-loop iteration within a turn. So
        a single stored value is an upper bound on real context size, not a direct
        measurement of it. Returning the running max across turns gives a stable,
        monotonic high-water-mark suitable for a "context fill" gauge — cache TTL
        resets and per-turn iteration-count swings stop pulling the bar backwards.
        """
        max_total = 0
        for ev in self.read_events(conv_id):
            if ev.get("type") != "usage":
                continue
            total = (
                self._int_token(ev.get("input_tokens"))
                + self._int_token(ev.get("cache_creation_input_tokens"))
                + self._int_token(ev.get("cache_read_input_tokens"))
            )
            if total > max_total:
                max_total = total
        return max_total

    def write_summary(self, conv_id: str, content: str) -> None:
        lock_path = self._lock_path(conv_id)
        with lock_path.open("a") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                target = self.summary_path_for(conv_id)
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    "w", dir=target.parent, prefix=".tmp-", suffix=".md", delete=False
                ) as f:
                    f.write(content)
                    tmp_path = Path(f.name)
                tmp_path.replace(target)
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)

    def list_all(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for month_dir in self._root.iterdir():
            if not month_dir.is_dir():
                continue
            for path in month_dir.glob("*.json"):
                if path.name.endswith(".tmp"):
                    continue
                stat = path.stat()
                items.append({
                    "id": path.stem,
                    "mtime": stat.st_mtime,
                    "path": str(path),
                    "has_summary": (path.parent / f"{path.stem}.summary.md").exists(),
                })
        items.sort(key=lambda x: x["mtime"], reverse=True)
        return items

    def idle_seconds_since_last_event(
        self, conv_id: str, now: datetime | None = None
    ) -> float | None:
        """Return seconds since the most-recent timestamped event, or None."""
        now = now or datetime.now(timezone.utc)
        events = self.read_events(conv_id)
        for ev in reversed(events):
            ts_str = ev.get("ts") or ev.get("created_ts")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return (now - ts).total_seconds()
            except ValueError:
                continue
        return None

    @staticmethod
    def _blocks_text(blocks: list[dict[str, Any]]) -> str:
        return "".join(
            block.get("text", "")
            for block in blocks
            if block.get("kind") == "text" and isinstance(block.get("text"), str)
        )

    @staticmethod
    def _int_token(value: Any) -> int:
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return 0
