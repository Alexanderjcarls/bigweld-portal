"""Decide whether a user message warrants pre-retrieval.

Skip only short meta-control messages that have no quoted entity and no
question mark. Everything else gets retrieval.
"""

import re


_QUOTED_PATTERN = re.compile(r'["\']([^"\']{2,})["\']')
_TOKEN_PATTERN = re.compile(r"\S+")


def should_skip_retrieval(text: str) -> bool:
    text = text.strip()
    if not text:
        return True

    tokens = _TOKEN_PATTERN.findall(text)
    if len(tokens) >= 6:
        return False

    if "?" in text:
        return False

    if _QUOTED_PATTERN.search(text):
        return False

    return True
