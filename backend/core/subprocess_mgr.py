"""Manage `claude -p` subprocess lifecycle for one turn.

Per-turn invocation: each user turn spawns a fresh subprocess; conversation
context persists via Claude's `--resume <session-uuid>` against its own session
storage. We mirror to our own JSONL via hooks.

Defensive fallback: if --resume errors (corrupt session, version skew), we
respawn with a fresh --session-id and pipe the prior transcript via stdin.

Critical subprocess details:
1. Always re-raise CancelledError so disconnects propagate.
2. Drain stderr in a separate task; POSIX pipes are small enough to deadlock.
3. terminate(), wait up to 5 seconds, then kill().
"""

import asyncio
import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from backend.core.stream_parser import LineBufferedParser, StreamJsonEvent, is_terminal

logger = logging.getLogger(__name__)


@dataclass
class ManagedProc:
    """Wraps an asyncio subprocess with drain state and test observability."""

    proc: asyncio.subprocess.Process
    env_seen: dict[str, str]
    stderr_collected: str = ""
    _stderr_task: asyncio.Task[None] | None = None
    _killed: bool = False
    _parser: LineBufferedParser = field(default_factory=LineBufferedParser)
    _replay_events: list[StreamJsonEvent] = field(default_factory=list)

    @property
    def returncode(self) -> int | None:
        return self.proc.returncode

    async def wait_closed(self) -> int:
        """Wait for the process and stderr drain task to fully complete."""
        await self.proc.wait()
        if self._stderr_task is not None:
            await self._stderr_task
        return self.proc.returncode or 0


@dataclass
class SpawnResult:
    proc: ManagedProc
    new_session_uuid: str
    fallback_used: bool = False


class SubprocessManager:
    def __init__(
        self,
        claude_command: list[str] | None = None,
        per_turn_timeout_s: int = 300,
    ) -> None:
        self._claude_command = claude_command or ["claude"]
        self._per_turn_timeout_s = per_turn_timeout_s

    def _build_env(self, conversation_id: str, conversation_file: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = ""
        env["BIGWELD_CONVERSATION_ID"] = conversation_id
        env["BIGWELD_CONVERSATION_FILE"] = str(conversation_file)
        return env

    def _build_args(self, prompt: str, session_uuid: str, is_resume: bool) -> list[str]:
        session_flag = ["--resume", session_uuid] if is_resume else ["--session-id", session_uuid]
        return [
            "-p",
            prompt,
            *session_flag,
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]

    async def spawn_turn(
        self,
        prompt: str,
        session_uuid: str,
        is_resume: bool,
        conversation_id: str,
        conversation_file: Path,
        stdin_data: bytes | None = None,
    ) -> ManagedProc:
        env = self._build_env(conversation_id, conversation_file)
        args = self._build_args(prompt, session_uuid, is_resume)
        proc = await asyncio.create_subprocess_exec(
            *self._claude_command,
            *args,
            stdin=asyncio.subprocess.PIPE if stdin_data is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        managed = ManagedProc(
            proc=proc,
            env_seen={
                "ANTHROPIC_API_KEY": env["ANTHROPIC_API_KEY"],
                "BIGWELD_CONVERSATION_ID": env["BIGWELD_CONVERSATION_ID"],
                "BIGWELD_CONVERSATION_FILE": env["BIGWELD_CONVERSATION_FILE"],
            },
        )
        managed._stderr_task = asyncio.create_task(self._drain_stderr(managed))
        if stdin_data is not None:
            assert proc.stdin is not None
            try:
                if stdin_data:
                    proc.stdin.write(stdin_data)
                    await proc.stdin.drain()
                proc.stdin.close()
            except (BrokenPipeError, ConnectionResetError):
                pass
        return managed

    async def _drain_stderr(self, managed: ManagedProc) -> None:
        assert managed.proc.stderr is not None
        while True:
            line = await managed.proc.stderr.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            managed.stderr_collected += decoded
            if "fatal:" in decoded.lower():
                logger.error("subprocess fatal: %s", decoded.strip())

    async def stream_events(self, managed: ManagedProc) -> AsyncIterator[StreamJsonEvent]:
        """Yield parsed stream-json events and clean up on cancellation."""
        completed = False
        try:
            while managed._replay_events:
                event = managed._replay_events.pop(0)
                yield event
                if is_terminal(event):
                    completed = True
                    await managed.wait_closed()
                    return

            while True:
                events, stream_closed = await self._read_stdout_events(managed)
                if not events and stream_closed:
                    completed = True
                    return

                for event in events:
                    yield event
                    if is_terminal(event):
                        completed = True
                        await managed.wait_closed()
                        return

                if stream_closed:
                    completed = True
                    return
        except asyncio.CancelledError:
            await self._kill(managed)
            raise
        finally:
            if not completed:
                if managed.proc.returncode is None:
                    await self._kill(managed)
                else:
                    await managed.wait_closed()

    async def _read_stdout_events(
        self,
        managed: ManagedProc,
    ) -> tuple[list[StreamJsonEvent], bool]:
        assert managed.proc.stdout is not None
        while True:
            try:
                chunk = await asyncio.wait_for(
                    managed.proc.stdout.read(8192),
                    timeout=self._per_turn_timeout_s,
                )
            except asyncio.TimeoutError:
                logger.warning("subprocess turn timeout; terminating")
                await self._kill(managed)
                return (
                    [
                        {
                            "type": "system",
                            "subtype": "error",
                            "error": "turn timeout",
                            "is_error": True,
                        }
                    ],
                    True,
                )

            if not chunk:
                events = list(managed._parser.eof())
                await managed.wait_closed()
                return events, True

            events = list(managed._parser.feed(chunk))
            if events:
                return events, False

    async def _read_next_event(self, managed: ManagedProc) -> StreamJsonEvent | None:
        if managed._replay_events:
            return managed._replay_events.pop(0)

        events, _stream_closed = await self._read_stdout_events(managed)
        if not events:
            return None

        first, rest = events[0], events[1:]
        managed._replay_events.extend(rest)
        return first

    async def _kill(self, managed: ManagedProc) -> None:
        if managed._killed:
            await managed.wait_closed()
            return

        managed._killed = True
        if managed.proc.returncode is None:
            try:
                managed.proc.terminate()
                try:
                    await asyncio.wait_for(managed.proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    logger.warning("subprocess did not exit on terminate; killing")
                    managed.proc.kill()
                    await managed.proc.wait()
            except ProcessLookupError:
                pass

        await managed.wait_closed()

    async def spawn_turn_with_fallback(
        self,
        prompt: str,
        session_uuid: str,
        is_resume: bool,
        conversation_id: str,
        conversation_file: Path,
    ) -> SpawnResult:
        """Spawn a turn, retrying --resume errors with a fresh session."""
        managed = await self.spawn_turn(
            prompt=prompt,
            session_uuid=session_uuid,
            is_resume=is_resume,
            conversation_id=conversation_id,
            conversation_file=conversation_file,
        )
        first_event = await self._read_next_event(managed)

        if is_resume and first_event is not None and first_event.get("is_error"):
            await managed.wait_closed()
            transcript = self._read_transcript(conversation_file)
            stdin_data = conversation_file.read_bytes() if conversation_file.exists() else b""
            new_uuid = str(uuid.uuid4())
            full_prompt = self._assemble_fallback_prompt(transcript, prompt)
            fallback_managed = await self.spawn_turn(
                prompt=full_prompt,
                session_uuid=new_uuid,
                is_resume=False,
                conversation_id=conversation_id,
                conversation_file=conversation_file,
                stdin_data=stdin_data,
            )
            return SpawnResult(
                proc=fallback_managed,
                new_session_uuid=new_uuid,
                fallback_used=True,
            )

        if first_event is not None:
            managed._replay_events.insert(0, first_event)
        return SpawnResult(
            proc=managed,
            new_session_uuid=session_uuid,
            fallback_used=False,
        )

    @staticmethod
    def _read_transcript(conversation_file: Path) -> list[dict]:
        if not conversation_file.exists():
            return []

        events: list[dict] = []
        for line in conversation_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    @staticmethod
    def _assemble_fallback_prompt(transcript: list[dict], current: str) -> str:
        lines = ["### Prior conversation (for continuity - --resume fallback)"]
        for event in transcript:
            event_type = event.get("type")
            if event_type == "user":
                lines.append(f"User: {event.get('content', '')}")
            elif event_type == "assistant":
                lines.append(f"Assistant: {event.get('content', '')}")
        lines.append("\n### Current turn")
        lines.append(current)
        return "\n".join(lines)
