"""Manage `claude -p` subprocess lifecycle for one turn.

Per-turn invocation: each user turn spawns a fresh subprocess; conversation
context persists via Claude's `--resume <session-uuid>` against its own session
storage. We mirror to our own JSONL via hooks.

Defensive fallback: if --resume errors (corrupt session, version skew), we
respawn with a fresh --session-id and embed the prior transcript in the prompt.

Critical subprocess details:
1. Always re-raise CancelledError so disconnects propagate.
2. Drain stderr in a separate task; POSIX pipes are small enough to deadlock.
3. terminate(), wait up to 5 seconds, then kill().
"""

import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from backend.core.stream_parser import LineBufferedParser, StreamJsonEvent, is_terminal
from backend.metrics import resume_failure_total, subprocess_startup_seconds

logger = logging.getLogger(__name__)

ALLOWED_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "TZ"}
TEST_ENV_KEYS = {
    "MOCK_CLAUDE_MODE",
    "MOCK_CLAUDE_DELAY_MS",
    "MOCK_CLAUDE_PROMPT_FILE",
    "MOCK_CLAUDE_ECHO_STDIN",
    "MOCK_CLAUDE_RATE_LIMIT_ONCE_FILE",
}
PERMANENT_RESUME_ERROR_CODES = {"session_not_found", "corrupt_session"}


@dataclass
class ManagedProc:
    """Wraps an asyncio subprocess with drain state and test observability."""

    proc: asyncio.subprocess.Process
    env_seen: dict[str, str]
    stderr_collected: str = ""
    startup_started_at: float = field(default_factory=time.perf_counter)
    _startup_observed: bool = False
    _stderr_task: asyncio.Task[None] | None = None
    _killed: bool = False
    received_result: bool = False
    emitted_error: bool = False
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
        resume_retry_backoff_s: float = 0.2,
    ) -> None:
        self._claude_command = claude_command or ["claude"]
        self._per_turn_timeout_s = per_turn_timeout_s
        self._resume_retry_backoff_s = resume_retry_backoff_s

    def _build_env(self, conversation_id: str, conversation_file: Path) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if key in ALLOWED_ENV_KEYS or key in TEST_ENV_KEYS
        }
        env.update({
            "ANTHROPIC_API_KEY": "",
            "BIGWELD_PORTAL_ROOT": os.environ.get(
                "BIGWELD_PORTAL_ROOT",
                "/datapool/bigweld-portal",
            ),
            "BIGWELD_CONVERSATION_ID": conversation_id,
            "BIGWELD_CONVERSATION_FILE": str(conversation_file),
            "BIGWELD_BACKEND_ASSISTANT_BLOCKS": "1",
        })
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
    ) -> ManagedProc:
        env = self._build_env(conversation_id, conversation_file)
        args = self._build_args(prompt, session_uuid, is_resume)
        startup_started_at = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            *self._claude_command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        managed = ManagedProc(
            proc=proc,
            env_seen=dict(env),
            startup_started_at=startup_started_at,
        )
        managed._stderr_task = asyncio.create_task(self._drain_stderr(managed))
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
                self._record_event(managed, event)
                yield event
                if is_terminal(event):
                    completed = True
                    await managed.wait_closed()
                    return

            while True:
                events, stream_closed = await self._read_stdout_events(managed)
                if not events and stream_closed:
                    error = await self._missing_result_error(managed)
                    if error is not None:
                        self._record_event(managed, error)
                        yield error
                    completed = True
                    return

                for event in events:
                    self._record_event(managed, event)
                    yield event
                    if is_terminal(event):
                        completed = True
                        await managed.wait_closed()
                        return

                if stream_closed:
                    error = await self._missing_result_error(managed)
                    if error is not None:
                        self._record_event(managed, error)
                        yield error
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
                if events:
                    self._observe_startup(managed)
                await managed.wait_closed()
                return events, True

            events = list(managed._parser.feed(chunk))
            if events:
                self._observe_startup(managed)
                return events, False

    @staticmethod
    def _observe_startup(managed: ManagedProc) -> None:
        if managed._startup_observed:
            return
        managed._startup_observed = True
        subprocess_startup_seconds.observe(time.perf_counter() - managed.startup_started_at)

    @staticmethod
    def _record_event(managed: ManagedProc, event: StreamJsonEvent) -> None:
        if event.get("type") == "result":
            managed.received_result = True
        if event.get("is_error"):
            managed.emitted_error = True

    @staticmethod
    async def _missing_result_error(managed: ManagedProc) -> StreamJsonEvent | None:
        await managed.wait_closed()
        if managed.received_result or managed.emitted_error:
            return None
        return {
            "type": "system",
            "subtype": "error",
            "is_error": True,
            "error": f"subprocess exited rc={managed.returncode} before result",
        }

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
        """Spawn a turn, retrying transient --resume errors before fallback."""
        managed = await self.spawn_turn(
            prompt=prompt,
            session_uuid=session_uuid,
            is_resume=is_resume,
            conversation_id=conversation_id,
            conversation_file=conversation_file,
        )
        first_event = await self._read_next_event(managed)

        if is_resume and first_event is not None and first_event.get("is_error"):
            if not self._is_permanent_resume_error(first_event):
                await managed.wait_closed()
                await asyncio.sleep(self._resume_retry_backoff_s)
                retry_managed = await self.spawn_turn(
                    prompt=prompt,
                    session_uuid=session_uuid,
                    is_resume=True,
                    conversation_id=conversation_id,
                    conversation_file=conversation_file,
                )
                retry_first_event = await self._read_next_event(retry_managed)
                if retry_first_event is None or not retry_first_event.get("is_error"):
                    if retry_first_event is not None:
                        retry_managed._replay_events.insert(0, retry_first_event)
                    return SpawnResult(
                        proc=retry_managed,
                        new_session_uuid=session_uuid,
                        fallback_used=False,
                    )
                await retry_managed.wait_closed()
            else:
                await managed.wait_closed()

            return await self._spawn_fallback(
                prompt=prompt,
                conversation_id=conversation_id,
                conversation_file=conversation_file,
            )

        if first_event is not None:
            managed._replay_events.insert(0, first_event)
        return SpawnResult(
            proc=managed,
            new_session_uuid=session_uuid,
            fallback_used=False,
        )

    async def _spawn_fallback(
        self,
        *,
        prompt: str,
        conversation_id: str,
        conversation_file: Path,
    ) -> SpawnResult:
        transcript = self._read_transcript(conversation_file)
        new_uuid = str(uuid.uuid4())
        full_prompt = self._assemble_fallback_prompt(transcript, prompt)
        resume_failure_total.inc()
        fallback_managed = await self.spawn_turn(
            prompt=full_prompt,
            session_uuid=new_uuid,
            is_resume=False,
            conversation_id=conversation_id,
            conversation_file=conversation_file,
        )
        return SpawnResult(
            proc=fallback_managed,
            new_session_uuid=new_uuid,
            fallback_used=True,
        )

    @staticmethod
    def _is_permanent_resume_error(event: StreamJsonEvent) -> bool:
        subtype = str(event.get("subtype", "")).lower()
        error = str(event.get("error", "")).lower().replace(" ", "_")
        return subtype in PERMANENT_RESUME_ERROR_CODES or any(
            code in error for code in PERMANENT_RESUME_ERROR_CODES
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
                rendered = SubprocessManager._render_assistant_event(event)
                if rendered:
                    lines.append(f"Assistant: {rendered}")
            elif event_type == "tool_use_result":
                tool = event.get("tool") or event.get("name") or "?"
                output = str(event.get("output", ""))[:300]
                lines.append(f"[Tool {tool}: {output}]")
        lines.append("\n### Current turn")
        lines.append(current)
        return "\n".join(lines)

    @staticmethod
    def _render_assistant_event(event: dict) -> str:
        blocks = event.get("blocks")
        if isinstance(blocks, list):
            rendered: list[str] = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("kind") == "text" and isinstance(block.get("text"), str):
                    rendered.append(block["text"])
                elif block.get("kind") == "tool_use":
                    rendered.append(f"[ran tool: {block.get('name', 'tool')}]")
            return "\n".join(item for item in rendered if item)
        content = event.get("content")
        return content if isinstance(content, str) else ""
