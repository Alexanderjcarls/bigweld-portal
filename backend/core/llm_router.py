"""Two-provider LLM router: Together-tput primary, DeepInfra fallback.

Mirrors the Aegis V2 provider order for output-light summarization work.
Secrets are read from /aegis/.env through python-dotenv, with the process
environment available as a fallback for tests and local overrides.
"""
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

AEGIS_ENV = Path("/aegis/.env")

PROVIDERS = [
    {
        "name": "together-tput",
        "base_url": "https://api.together.xyz/v1",
        "key_env": "AEGIS_V2_TOGETHER_API_KEY",
        "model": "Qwen/Qwen3-235B-A22B-Instruct-2507-tput",
    },
    {
        "name": "deepinfra",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "key_env": "AEGIS_V2_DEEPINFRA_API_KEY",
        "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    },
]

PERMANENT_FAIL_CODES = {"model_not_available", "model_not_found"}
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def _read_keys() -> dict[str, str]:
    values = dict(os.environ)
    if AEGIS_ENV.exists():
        values.update({k: v for k, v in dotenv_values(AEGIS_ENV).items() if v is not None})
    return values


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _provider_error_code(body: dict[str, Any]) -> str | None:
    code = body.get("code")
    if isinstance(code, str) and code:
        return code

    error = body.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, str) and code:
            return code
    return None


def _should_fall_through(response: httpx.Response, body: dict[str, Any]) -> bool:
    if response.status_code in TRANSIENT_STATUS_CODES:
        return True
    if response.status_code in (400, 404):
        return _provider_error_code(body) in PERMANENT_FAIL_CODES
    return False


async def chat(messages: list[dict], temperature: float = 0.7) -> str:
    keys = _read_keys()
    last_error: Exception | None = None

    for provider in PROVIDERS:
        api_key = keys.get(provider["key_env"])
        if not api_key:
            logger.warning("router: no key for %s, skipping", provider["name"])
            continue

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{provider['base_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": provider["model"],
                        "messages": messages,
                        "temperature": temperature,
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            logger.warning("router: %s network failure: %s; falling back", provider["name"], exc)
            continue
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("router: %s transport failure: %s; falling back", provider["name"], exc)
            continue

        body = _json_or_empty(response)
        if response.is_error:
            if _should_fall_through(response, body):
                code = _provider_error_code(body) or f"http_{response.status_code}"
                last_error = RuntimeError(f"{provider['name']} failed with {code}")
                logger.warning(
                    "router: %s fallback-eligible error %s; falling back",
                    provider["name"],
                    code,
                )
                continue
            response.raise_for_status()

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"{provider['name']} returned an invalid chat response") from exc

    raise RuntimeError(f"all LLM providers failed; last={last_error}")
