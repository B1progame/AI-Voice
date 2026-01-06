import requests
import json as _json
from typing import Generator

from backend.core.config import settings
from backend.core.logging_setup import get_logger

LOG = get_logger(__name__)


def chat_completion(messages: list[dict], *, temperature: float | None = None, max_tokens: int | None = None) -> str:
    """Gets a single (non-streaming) completion from Ollama /api/chat.

    Used for the Stage 1.5 planner phase, where we need strict JSON.
    """
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 8192,  # <--- WICHTIG: Erweitert das Gedächtnis für den Planer
        }
    }
    
    if temperature is not None:
        payload["options"]["temperature"] = temperature
    if max_tokens is not None:
        payload["options"]["num_predict"] = max_tokens

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        msg = (data or {}).get("message") or {}
        content = msg.get("content")
        if not isinstance(content, str):
            return ""
        return content
    except Exception as e:
        LOG.error(f"Ollama chat_completion failed: {e}")
        return ""


def stream_chat_completion(messages: list[dict]) -> Generator[str, None, None]:
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/chat"
    
    # HIER IST DIE WICHTIGSTE ÄNDERUNG:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": 4096,  # <--- WICHTIG: Erweitert das Gedächtnis für die Antwort
            "temperature": 0.7
        }
    }

    LOG.info("Calling Ollama model=%s msgs=%s ctx=4096", settings.OLLAMA_MODEL, len(messages))

    with requests.post(url, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = line
                # Ollama returns JSON per line
                j = _json.loads(data)
                if j.get("done") is True:
                    break
                msg = j.get("message") or {}
                content = msg.get("content")
                if content:
                    yield content
            except Exception:
                continue