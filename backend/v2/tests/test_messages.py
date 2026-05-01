from uuid import uuid4

import pytest

from backend.v2.db.messages import (
    load_anthropic_messages,
    persist_anthropic_message,
    total_token_count,
)


@pytest.mark.asyncio(loop_scope="session")
async def test_persist_and_load_round_trip(pg_conn):
    conv_id = uuid4()
    await pg_conn.execute(
        "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, 'test')", conv_id
    )

    user_content = [{"type": "text", "text": "hello"}]
    assistant_content = [
        {"type": "text", "text": "Hi there"},
        {"type": "tool_use", "id": "toolu_1", "name": "get_node", "input": {"slug": "x"}},
    ]
    tool_result_content = [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_1",
            "content": [{"type": "text", "text": "node x"}],
        }
    ]

    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "user",
        user_content,
        turn_idx=0,
        token_count=10,
    )
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "assistant",
        assistant_content,
        turn_idx=1,
        token_count=150,
    )
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "user",
        tool_result_content,
        turn_idx=2,
    )

    history = await load_anthropic_messages(pg_conn, conv_id)
    assert len(history) == 3
    assert history[0] == {"role": "user", "content": user_content}
    assert history[1] == {"role": "assistant", "content": assistant_content}
    assert history[2] == {"role": "user", "content": tool_result_content}


@pytest.mark.asyncio(loop_scope="session")
async def test_load_strips_legacy_orphan_tool_use_blocks(pg_conn):
    conv_id = uuid4()
    await pg_conn.execute(
        "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, 'test')", conv_id
    )
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "user",
        [{"type": "text", "text": "check this"}],
        turn_idx=0,
    )
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "assistant",
        [
            {"type": "text", "text": "I will look."},
            {"type": "tool_use", "id": "toolu_orphan", "name": "get_node", "input": {}},
        ],
        turn_idx=1,
    )
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "user",
        [{"type": "text", "text": "next normal turn"}],
        turn_idx=2,
    )

    history = await load_anthropic_messages(pg_conn, conv_id)
    assert history == [
        {"role": "user", "content": [{"type": "text", "text": "check this"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "I will look."}]},
        {"role": "user", "content": [{"type": "text", "text": "next normal turn"}]},
    ]


@pytest.mark.asyncio(loop_scope="session")
async def test_persist_preserves_thinking_signature(pg_conn):
    """thinking blocks have a `signature` field that Anthropic requires on replay."""
    conv_id = uuid4()
    await pg_conn.execute(
        "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, 'test')", conv_id
    )
    content = [
        {"type": "thinking", "thinking": "Let me think...", "signature": "abc123sig"},
        {"type": "text", "text": "answer"},
    ]
    await persist_anthropic_message(pg_conn, conv_id, "assistant", content, turn_idx=0)
    history = await load_anthropic_messages(pg_conn, conv_id)
    assert history[0]["content"][0]["signature"] == "abc123sig"


@pytest.mark.asyncio(loop_scope="session")
async def test_total_token_count_uses_max_not_sum(pg_conn):
    """Anthropic usage is cumulative-within-turn; take MAX not SUM."""
    conv_id = uuid4()
    await pg_conn.execute(
        "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, 'test')", conv_id
    )
    await persist_anthropic_message(pg_conn, conv_id, "user", [], turn_idx=0, token_count=100)
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "assistant",
        [],
        turn_idx=1,
        token_count=500,
    )
    await persist_anthropic_message(pg_conn, conv_id, "user", [], turn_idx=2, token_count=520)
    await persist_anthropic_message(
        pg_conn,
        conv_id,
        "assistant",
        [],
        turn_idx=3,
        token_count=900,
    )

    total = await total_token_count(pg_conn, conv_id)
    assert total == 900
