"""Render retrieved context as a system-prompt block."""

from __future__ import annotations

from typing import Any


DEFAULT_CONTEXT_TOKEN_BUDGET = 3500
_CHARS_PER_TOKEN = 4


def render_retrieved_context(
    entities: list[dict[str, Any]],
    expansion: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
) -> str:
    if not entities and not expansion and not summaries:
        return ""

    max_chars = token_budget * _CHARS_PER_TOKEN
    lines = ["<retrieved_context>"]
    char_count = len(lines[0])

    if entities:
        char_count = _append(lines, char_count, max_chars, "## Entities (vector match)")
        for entity in entities:
            char_count = _append(
                lines,
                char_count,
                max_chars,
                "- [{label}] **{name}** ({slug}) - {description}; confidence={confidence}".format(
                    label=entity.get("label", "Entity"),
                    name=entity.get("name") or entity.get("title") or entity.get("slug", "unknown"),
                    slug=entity.get("slug", "unknown"),
                    description=entity.get("description") or entity.get("summary") or "(no description)",
                    confidence=entity.get("confidence", "unknown"),
                ),
            )

    if expansion:
        char_count = _append(lines, char_count, max_chars, "")
        char_count = _append(lines, char_count, max_chars, "## Related (1-hop expansion)")
        for neighbor in expansion:
            char_count = _append(
                lines,
                char_count,
                max_chars,
                "- [{label}] **{name}** ({slug}) - {edge_type} from {from_slug}".format(
                    label=neighbor.get("label", "Entity"),
                    name=neighbor.get("name") or neighbor.get("title") or neighbor.get("slug", "unknown"),
                    slug=neighbor.get("slug", "unknown"),
                    edge_type=neighbor.get("edge_type", "RELATED"),
                    from_slug=neighbor.get("from_slug", "unknown"),
                ),
            )

    if summaries:
        char_count = _append(lines, char_count, max_chars, "")
        char_count = _append(lines, char_count, max_chars, "## Cross-conversation context")
        for summary in summaries:
            snippet = str(summary.get("summary", ""))[:200]
            suffix = "..." if len(str(summary.get("summary", ""))) > 200 else ""
            char_count = _append(
                lines,
                char_count,
                max_chars,
                f"- From '{summary.get('conv_title', 'Untitled conversation')}': {snippet}{suffix}",
            )

    lines.append("</retrieved_context>")
    return "\n".join(lines)


def _append(lines: list[str], char_count: int, max_chars: int, line: str) -> int:
    if char_count + len(line) + 1 > max_chars:
        return char_count
    lines.append(line)
    return char_count + len(line) + 1
