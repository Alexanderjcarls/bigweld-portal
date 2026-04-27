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
        return json_path.with_suffix("").with_suffix(".summary.md") if False else (
            json_path.parent / f"{json_path.stem}.summary.md"
        )

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
