from __future__ import annotations

from backend.services.tools.context import ToolContext
from backend.services.tools.web_search import run as web_search_run


def run(args: dict, ctx: ToolContext) -> dict:
    query = (args or {}).get("query")
    if isinstance(query, str):
        query = query.strip()
    else:
        query = ""

    # Keep it simple: rely on the configured search backend.
    # The LLM must produce the final recipe answer and include sources.
    search_query = query if query.lower().startswith("rezept") else f"Rezept {query}".strip()

    res = web_search_run({"query": search_query, "max_results": 5}, ctx)
    res["original_query"] = query
    res["tool"] = "recipe_search"
    return res