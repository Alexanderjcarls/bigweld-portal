from backend.v2.retrieval.render import render_retrieved_context


def test_render_includes_entities_and_summaries():
    entities = [
        {
            "slug": "case-reopen",
            "label": "Capability",
            "name": "Case Reopen",
            "description": "Reopens closed cases on email reply within 30 days",
            "confidence": "verified",
        },
    ]
    expansion = [
        {
            "slug": "func-x",
            "label": "Functionality",
            "name": "Email reply listener",
            "edge_type": "ENABLES",
            "from_slug": "case-reopen",
        },
    ]
    summaries = [
        {
            "summary": "Discussed case-reopen 30-day window logic",
            "conv_title": "SFDC migration prep",
        },
    ]
    block = render_retrieved_context(entities, expansion, summaries)

    assert "<retrieved_context>" in block
    assert "case-reopen" in block
    assert "Email reply listener" in block
    assert "ENABLES" in block
    assert "SFDC migration prep" in block


def test_render_handles_empty():
    block = render_retrieved_context([], [], [])
    assert block == ""
