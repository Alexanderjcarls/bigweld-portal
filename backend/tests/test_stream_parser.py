"""Stream parser tests - chunk-boundary handling is the load-bearing case."""

import json

from backend.core.stream_parser import LineBufferedParser, is_terminal


def test_full_line_in_one_chunk():
    parser = LineBufferedParser()
    events = list(parser.feed(b'{"type":"system","subtype":"init"}\n'))
    assert events == [{"type": "system", "subtype": "init"}]


def test_event_split_across_chunks():
    """The #1 bug: lines straddle TCP chunk boundaries."""
    parser = LineBufferedParser()
    events = list(parser.feed(b'{"type":"system",'))
    assert events == []  # incomplete - buffer holds it
    events = list(parser.feed(b'"subtype":"init"}\n'))
    assert events == [{"type": "system", "subtype": "init"}]


def test_multiple_events_one_chunk():
    parser = LineBufferedParser()
    chunk = (
        b'{"type":"system","subtype":"init"}\n'
        b'{"type":"assistant","message":{"role":"assistant"}}\n'
    )
    events = list(parser.feed(chunk))
    assert len(events) == 2
    assert events[0]["type"] == "system"
    assert events[1]["type"] == "assistant"


def test_partial_line_across_three_chunks():
    parser = LineBufferedParser()
    assert list(parser.feed(b'{"type":')) == []
    assert list(parser.feed(b'"system",')) == []
    events = list(parser.feed(b'"subtype":"init"}\n'))
    assert events == [{"type": "system", "subtype": "init"}]


def test_malformed_json_skipped():
    """A bad line is logged and skipped; subsequent good lines parse."""
    parser = LineBufferedParser()
    chunk = b"not valid json\n" + b'{"type":"system"}\n'
    events = list(parser.feed(chunk))
    assert events == [{"type": "system"}]


def test_eof_with_partial_line_logs_and_returns():
    parser = LineBufferedParser()
    list(parser.feed(b'{"type":"system"'))  # no newline
    # On eof(), the partial line should be flushed (parsed if valid, else dropped)
    final = list(parser.eof())
    assert final == [{"type": "system"}]


def test_eof_with_garbage_partial_line():
    parser = LineBufferedParser()
    list(parser.feed(b"garbage no newline"))
    final = list(parser.eof())
    assert final == []  # partial line was malformed -> dropped


def test_empty_chunk():
    parser = LineBufferedParser()
    assert list(parser.feed(b"")) == []


def test_is_terminal_for_result():
    assert is_terminal({"type": "result", "session_id": "x"}) is True
    assert is_terminal({"type": "system", "subtype": "init"}) is False
    assert is_terminal({"type": "assistant"}) is False


def test_unicode_event():
    parser = LineBufferedParser()
    events = list(parser.feed('{"type":"assistant","content":"hëllo 你好"}\n'.encode()))
    assert events == [{"type": "assistant", "content": "hëllo 你好"}]


def test_recognizes_top_level_rate_limit_event():
    """rate_limit_event is a top-level type, not a system/ subtype (spike finding)."""
    parser = LineBufferedParser()
    events = list(parser.feed(b'{"type":"rate_limit_event","wait_seconds":45}\n'))
    assert events == [{"type": "rate_limit_event", "wait_seconds": 45}]
    # Confirm is_terminal correctly says NO for this:
    assert is_terminal(events[0]) is False


def test_result_envelope_has_full_shape():
    """Result envelope from spike has subtype, is_error, total_cost_usd, usage, etc."""
    parser = LineBufferedParser()
    sample = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 2152,
        "result": "'pluto orbits backwards'",
        "session_id": "78d6a16d-d52c-4c62-a7c6-b38cb2f9d876",
        "total_cost_usd": 0.024,
        "usage": {"input_tokens": 6, "output_tokens": 16},
    }
    events = list(parser.feed((json.dumps(sample) + "\n").encode()))
    assert len(events) == 1
    assert events[0]["type"] == "result"
    assert events[0]["subtype"] == "success"
    assert events[0]["is_error"] is False
    assert events[0]["total_cost_usd"] == 0.024
    assert is_terminal(events[0]) is True
