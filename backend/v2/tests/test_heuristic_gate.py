from backend.v2.retrieval.heuristic_gate import should_skip_retrieval


def test_skip_short_meta_message():
    assert should_skip_retrieval("yes") is True
    assert should_skip_retrieval("Run it") is True
    assert should_skip_retrieval("thanks") is True


def test_skip_short_no_question():
    assert should_skip_retrieval("ok") is True


def test_no_skip_substantive_message():
    assert should_skip_retrieval("explain the case-reopen flow for SFDC") is False
    assert should_skip_retrieval("What does the storage SDE do?") is False


def test_no_skip_short_with_entity_quoted():
    assert should_skip_retrieval('about "case-reopen"?') is False


def test_no_skip_short_with_question_mark():
    assert should_skip_retrieval("anything?") is False
