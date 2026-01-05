from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response

logger = logging.getLogger("request")


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        status = getattr(locals().get("response", None), "status_code", "ERR")
        logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, status, duration_ms)