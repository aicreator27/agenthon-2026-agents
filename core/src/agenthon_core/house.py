"""Minimal audited House endpoint client; unused by the numeric-only MVP."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class HouseUnavailable(RuntimeError):
    pass


def house_available() -> bool:
    return all(os.getenv(name) for name in ("MODEL_ENDPOINT", "MODEL_NAME", "MODEL_TOKEN"))


def chat_json(
    *, system: str, user: str, max_tokens: int = 1200, temperature: float = 0.0
) -> dict[str, Any]:
    """Call only the organizer route and parse one JSON object."""
    if not house_available():
        raise HouseUnavailable("House environment variables are incomplete")
    if not 1 <= max_tokens <= 4000:
        raise ValueError("max_tokens must be between 1 and 4000")
    endpoint = os.environ["MODEL_ENDPOINT"].rstrip("/") + "/v1/chat/completions"
    body = json.dumps(
        {
            "model": os.environ["MODEL_NAME"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['MODEL_TOKEN']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.removeprefix("```json").removeprefix("```")
            content = content.removesuffix("```").strip()
        parsed = json.loads(content)
    except (OSError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise HouseUnavailable("House response was unavailable or not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HouseUnavailable("House response must be a JSON object")
    return parsed

