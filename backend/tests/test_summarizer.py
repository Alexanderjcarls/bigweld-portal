from datetime import datetime, timedelta, timezone

from backend.core.conversation_store import ConversationStore
from backend.core.summarizer import summarize_conversation, sweep_idle_conversations


async def _seed_old_conv(store, hours_old=25, with_content=True):
    conv_id = store.create()
    path = store.path_for(conv_id)
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_old)).isoformat()
    with path.open("a") as f:
        if with_content:
            f.write(f'{{"type":"user","content":"hello","ts":"{ts}"}}\n')
            f.write(f'{{"type":"assistant","content":"hi back","ts":"{ts}"}}\n')
    return conv_id


async def test_summarize_writes_md(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))
    store = ConversationStore(root=tmp_path / "conversations")
    conv_id = await _seed_old_conv(store)

    async def fake_chat(messages, temperature=0.7):
        return "## Decisions\n- agreed on X"

    monkeypatch.setattr("backend.core.summarizer.chat", fake_chat)

    out = await summarize_conversation(store, conv_id)
    assert out is not None
    assert store.summary_path_for(conv_id).read_text().startswith("## Decisions")


async def test_sweep_finds_only_idle_conversations(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))
    store = ConversationStore(root=tmp_path / "conversations")
    old = await _seed_old_conv(store, hours_old=25)
    fresh = await _seed_old_conv(store, hours_old=1)

    async def fake_chat(messages, temperature=0.7):
        return "## summary"

    monkeypatch.setattr("backend.core.summarizer.chat", fake_chat)

    n = await sweep_idle_conversations(store)
    assert n == 1
    assert store.summary_path_for(old).exists()
    assert not store.summary_path_for(fresh).exists()
