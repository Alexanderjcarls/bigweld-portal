"""LLM router provider fallback tests."""
import json
from pathlib import Path

import pytest

from backend.core import llm_router


@pytest.fixture(autouse=True)
def isolate_llm_keys(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(llm_router, "AEGIS_ENV", tmp_path / ".env")
    for provider in llm_router.PROVIDERS:
        monkeypatch.delenv(provider["key_env"], raising=False)


def _provider_url(provider: dict[str, str]) -> str:
    return f"{provider['base_url']}/chat/completions"


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _set_key(monkeypatch, provider: dict[str, str], value: str = "test-key") -> None:
    monkeypatch.setenv(provider["key_env"], value)


async def test_primary_success_no_fallback(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    secondary = llm_router.PROVIDERS[1]
    _set_key(monkeypatch, primary)
    _set_key(monkeypatch, secondary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(primary),
        json=_completion("primary answer"),
    )

    result = await llm_router.chat([{"role": "user", "content": "hello"}])

    assert result == "primary answer"
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert str(requests[0].url) == _provider_url(primary)


async def test_primary_429_falls_back_to_secondary(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    secondary = llm_router.PROVIDERS[1]
    _set_key(monkeypatch, primary)
    _set_key(monkeypatch, secondary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(primary),
        status_code=429,
        json={"error": {"code": "rate_limited"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(secondary),
        json=_completion("secondary answer"),
    )

    result = await llm_router.chat([{"role": "user", "content": "hello"}])

    assert result == "secondary answer"
    assert [str(request.url) for request in httpx_mock.get_requests()] == [
        _provider_url(primary),
        _provider_url(secondary),
    ]


async def test_primary_model_not_available_falls_back(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    secondary = llm_router.PROVIDERS[1]
    _set_key(monkeypatch, primary)
    _set_key(monkeypatch, secondary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(primary),
        status_code=400,
        json={"error": {"code": "model_not_available"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(secondary),
        json=_completion("fallback answer"),
    )

    result = await llm_router.chat([{"role": "user", "content": "hello"}])

    assert result == "fallback answer"


async def test_both_providers_failing_raises(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    secondary = llm_router.PROVIDERS[1]
    _set_key(monkeypatch, primary)
    _set_key(monkeypatch, secondary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(primary),
        status_code=500,
        json={"error": {"code": "server_error"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(secondary),
        status_code=500,
        json={"error": {"code": "server_error"}},
    )

    with pytest.raises(RuntimeError, match="all LLM providers failed"):
        await llm_router.chat([{"role": "user", "content": "hello"}])


async def test_missing_api_key_skipped(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    secondary = llm_router.PROVIDERS[1]
    monkeypatch.delenv(primary["key_env"], raising=False)
    _set_key(monkeypatch, secondary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(secondary),
        json=_completion("secondary only"),
    )

    result = await llm_router.chat([{"role": "user", "content": "hello"}])

    assert result == "secondary only"
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert str(requests[0].url) == _provider_url(secondary)


async def test_malformed_response_body_raises_clean_error(httpx_mock, monkeypatch):
    primary = llm_router.PROVIDERS[0]
    _set_key(monkeypatch, primary)
    httpx_mock.add_response(
        method="POST",
        url=_provider_url(primary),
        text="not json",
    )

    with pytest.raises(RuntimeError, match="returned an invalid chat response"):
        await llm_router.chat([{"role": "user", "content": "hello"}])

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload["model"] == primary["model"]
