from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, List, Optional

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Minimal Ollama streaming chat client.
    Uses Ollama HTTP API /api/chat with stream=true.
    Ollama API docs: official repository.  [oai_citation:6‡GitHub](https://github.com/ollama/ollama/blob/main/docs/api.md?utm_source=chatgpt.com)
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def stream_chat(self, *, model: str, messages: List[Dict[str, str]], timeout_s: float = 600.0) -> AsyncIterator[str]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=10.0)) as client:
            try:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            # Ollama should send JSON lines; if not, log and skip
                            logger.warning("Non-JSON line from Ollama: %r", line[:200])
                            continue

                        # Typical streaming object has fields: message.content, done
                        if obj.get("done") is True:
                            break

                        msg = obj.get("message") or {}
                        content = msg.get("content")
                        if content:
                            yield content
            except httpx.HTTPError as e:
                logger.exception("Ollama HTTP error")
                raise RuntimeError(f"Ollama request failed: {e}") from e


ollama_client = OllamaClient(settings.ollama_url)