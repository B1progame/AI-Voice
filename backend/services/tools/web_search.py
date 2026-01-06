from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

import httpx

from backend.core.config import settings
from backend.core.logging_setup import get_logger
from backend.services.tools.context import ToolContext
from backend.services.tools.errors import ToolError

LOG = get_logger(__name__)


def _build_search_url(base: str) -> str:
    b = (base or "").strip()
    if not b:
        return ""
    # Support both "http://host" and "http://host/search".
    if b.endswith("/search"):
        return b
    if not b.endswith("/"):
        b += "/"
    return urljoin(b, "search")


def run(args: dict, ctx: ToolContext) -> dict:
    searx_url = settings.SEARXNG_URL
    if not searx_url:
        raise ToolError(
            "Web search ist nicht konfiguriert. Setze in .env: SEARXNG_URL=http://<host>:<port> (z.B. dein lokales SearXNG)."
        )

    query = (args or {}).get("query")
    if not isinstance(query, str) or not query.strip():
        raise ToolError("query is required")
    query = query.strip()

    max_results = (args or {}).get("max_results", 5)
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 5
    
    # Wir begrenzen auf maximal 3 Ergebnisse, um Token zu sparen
    max_results = max(1, min(3, max_results))

    url = _build_search_url(searx_url)
    if not url:
        raise ToolError("SEARXNG_URL ist ungültig")

    params = {
        "q": query,
        "format": "json",
        "language": "de",
        "safesearch": 0,
    }

    t0 = datetime.utcnow()
    try:
        timeout = httpx.Timeout(connect=5.0, read=settings.SEARCH_TIMEOUT_SECONDS, write=10.0, pool=10.0)
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.TimeoutException:
        raise ToolError("Search request timeout")
    except Exception as e:
        LOG.exception("Search request failed")
        raise ToolError("Search request failed") from e
    finally:
        dt_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        LOG.info("tool=web_search duration_ms=%s max_results=%s", dt_ms, max_results)

    results = data.get("results") or []
    out = []
    
    for item in results[:max_results]:
        title = item.get("title")
        url_ = item.get("url")
        content = item.get("content") or item.get("snippet") or ""
        
        if not title and not url_:
            continue
            
        # --- FIX START: Text kürzen ---
        # Wir kürzen den Inhalt auf 800 Zeichen, damit Ollama nicht abstürzt.
        if len(content) > 800:
            content = content[:800] + "..."
        # --- FIX ENDE ---

        out.append({
            "title": (title or "").strip(),
            "url": (url_ or "").strip(),
            "snippet": content.strip(),
        })

    return {
        "query": query,
        "engine": "searxng",
        "results": out,
    }