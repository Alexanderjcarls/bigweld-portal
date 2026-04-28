from backend.core.assistant_blocks import AssistantBlockCollector


def test_assistant_block_collector_preserves_text_tool_text_order():
    collector = AssistantBlockCollector()

    for event in [
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "text"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "pre"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "tool_use", "id": "toolu_1", "name": "Bash"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "input_json_delta", "partial_json": "{\"command\":\"printf ok\"}"},
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": "ok",
                    },
                ],
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"type": "text"},
            },
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "post"},
            },
        },
    ]:
        collector.ingest(event)

    assert collector.blocks == [
        {"kind": "text", "text": "pre"},
        {
            "kind": "tool_use",
            "id": "toolu_1",
            "name": "Bash",
            "input": {"command": "printf ok"},
            "isStreaming": False,
            "output": "ok",
            "error": None,
        },
        {"kind": "text", "text": "post"},
    ]
    assert collector.text_content() == "prepost"
