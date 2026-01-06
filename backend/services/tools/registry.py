from __future__ import annotations

import time
from typing import Any, Callable

from pydantic import BaseModel, Field

from backend.core.logging_setup import get_logger
from backend.services.tools.context import ToolContext
from backend.services.tools.errors import ToolError

from backend.services.tools import get_datetime as tool_get_datetime
from backend.services.tools import get_weather as tool_get_weather
from backend.services.tools import web_search as tool_web_search
from backend.services.tools import recipe_search as tool_recipe_search

LOG = get_logger(__name__)


class _BaseArgs(BaseModel):
    model_config = {
        "extra": "ignore",
    }


class GetDateTimeArgs(_BaseArgs):
    pass


class GetWeatherArgs(_BaseArgs):
    location: str | None = None


class WebSearchArgs(_BaseArgs):
    query: str
    max_results: int = Field(default=5, ge=1, le=10)


class RecipeSearchArgs(_BaseArgs):
    query: str


ToolFn = Callable[[dict, ToolContext], dict]


TOOL_ALLOWLIST: dict[str, dict[str, Any]] = {
    "get_datetime": {
        "args_model": GetDateTimeArgs,
        "fn": tool_get_datetime.run,
    },
    "get_weather": {
        "args_model": GetWeatherArgs,
        "fn": tool_get_weather.run,
    },
    "web_search": {
        "args_model": WebSearchArgs,
        "fn": tool_web_search.run,
    },
    "recipe_search": {
        "args_model": RecipeSearchArgs,
        "fn": tool_recipe_search.run,
    },
}


def validate_tool_call(tool: str, args: Any) -> tuple[str, dict]:
    if tool not in TOOL_ALLOWLIST:
        raise ToolError(f"Tool not allowlisted: {tool}")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolError("args must be an object")

    model_cls = TOOL_ALLOWLIST[tool]["args_model"]
    try:
        m = model_cls(**args)
    except Exception as e:
        raise ToolError(f"Invalid args for {tool}: {e}")
    return tool, m.model_dump()


def run_tool(tool: str, args: dict, ctx: ToolContext) -> dict:
    """Run tool with validation + logging.

    Returns a dict that is safe to show to end-users / LLM.
    """
    tool, args = validate_tool_call(tool, args)
    fn: ToolFn = TOOL_ALLOWLIST[tool]["fn"]

    start = time.perf_counter()
    ok_flag: bool | None = None
    try:
        result = fn(args, ctx)
        if not isinstance(result, dict):
            raise ToolError(f"Tool {tool} returned non-object result")
        ok_flag = True
        return {
            "ok": True,
            "tool": tool,
            "args": args,
            "result": result,
        }
    except ToolError as te:
        ok_flag = False
        return {
            "ok": False,
            "tool": tool,
            "args": args,
            "error": {
                "code": te.code,
                "message": str(te),
            },
        }
    except Exception:
        ok_flag = False
        LOG.exception("Tool crashed: %s", tool)
        return {
            "ok": False,
            "tool": tool,
            "args": args,
            "error": {
                "code": "tool_crash",
                "message": "Tool execution failed",
            },
        }
    finally:
        dur_ms = int((time.perf_counter() - start) * 1000)
        LOG.info("tool=%s ok=%s duration_ms=%s", tool, ok_flag, dur_ms)