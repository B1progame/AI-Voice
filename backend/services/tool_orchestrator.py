from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.core.logging_setup import get_logger
from backend.services.ollama import chat_completion
from backend.services.tools.context import ToolContext
from backend.services.tools.registry import TOOL_ALLOWLIST, run_tool

LOG = get_logger(__name__)


@dataclass(frozen=True)
class PlannerDecision:
    action: str  # "respond" or "tool_call"
    tool: str | None = None
    args: dict | None = None


_PLANNER_SYSTEM_PROMPT = (
    "Du bist ein Planner für einen privaten AI Assistant. "
    "Du MUSST strikt JSON zurückgeben und darfst keinen Freitext schreiben. "
    "Deine Aufgabe: Entscheide, ob ein Tool notwendig ist, um die Frage zu beantworten.\n\n"
    
    "REGELN FÜR TOOLS:\n"
    "1. Wenn der Nutzer nach aktuellen Nachrichten, Feiertagen, Ferien, Events oder Fakten fragt, NUTZE 'web_search'.\n"
    "2. Wenn der Nutzer nach dem Wetter fragt, NUTZE 'get_weather'.\n"
    "3. Wenn der Nutzer nach Rezepten fragt, NUTZE 'recipe_search' oder 'web_search'.\n"
    "4. Wenn der Nutzer nur Hallo sagt oder Smalltalk macht, NUTZE 'respond'.\n"
    "\n"
    "Erlaubte Tools (Allowlist):\n"
    "- get_datetime args:{}\n"
    "- get_weather args:{location?:string}\n"
    "- web_search args:{query:string, max_results?:int}\n"
    "- recipe_search args:{query:string}\n"
    "\n"
    "Erlaubte JSON Antworten (exakt ein Objekt):\n"
    '{"action":"respond"}\n'
    'ODER {"action":"tool_call","tool":"web_search","args":{"query":"Ferien Rheinland-Pfalz 2026"}}\n'
    'ODER {"action":"tool_call","tool":"get_weather","args":{"location":"Berlin"}}\n'
)


def _try_parse_json(text: str) -> dict | None:
    if not text:
        return None
    t = text.strip()
    # Some models might wrap in code fences. Try to extract first JSON object.
    if "```" in t:
        # naive extraction
        parts = [p.strip() for p in t.split("```") if p.strip()]
        # choose the biggest part that starts with { and ends with }
        for p in sorted(parts, key=len, reverse=True):
            if p.startswith("{") and p.endswith("}"):
                t = p
                break
            if p.startswith("json"):
                p2 = p[4:].strip()
                if p2.startswith("{") and p2.endswith("}"):
                    t = p2
                    break
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def plan_action(llm_messages: list[dict]) -> PlannerDecision:
    """Phase 1: Ask the model to decide whether to call a tool.

    If anything is invalid, we fall back to Stage-1 behavior (respond).
    """
    planner_messages = [{"role": "system", "content": _PLANNER_SYSTEM_PROMPT}] + llm_messages[-8:]
    try:
        # NOTE: We use temperature=0.0 to get deterministic JSON
        raw = chat_completion(planner_messages, temperature=0.0, max_tokens=256)
    except Exception:
        LOG.exception("Planner request failed")
        return PlannerDecision(action="respond")

    obj = _try_parse_json(raw)
    if not obj:
        return PlannerDecision(action="respond")

    action = obj.get("action")
    if action == "respond":
        return PlannerDecision(action="respond")

    if action != "tool_call":
        return PlannerDecision(action="respond")

    tool = obj.get("tool")
    args = obj.get("args")
    if not isinstance(tool, str) or tool not in TOOL_ALLOWLIST:
        return PlannerDecision(action="respond")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return PlannerDecision(action="respond")

    return PlannerDecision(action="tool_call", tool=tool, args=args)


@dataclass(frozen=True)
class ToolRunOutcome:
    decision: PlannerDecision
    tool_payload: dict | None


def run_planned_tool(decision: PlannerDecision, ctx: ToolContext) -> ToolRunOutcome:
    if decision.action != "tool_call" or not decision.tool:
        return ToolRunOutcome(decision=PlannerDecision(action="respond"), tool_payload=None)

    payload = run_tool(decision.tool, decision.args or {}, ctx)
    return ToolRunOutcome(decision=decision, tool_payload=payload)


def build_final_messages(llm_messages: list[dict], outcome: ToolRunOutcome) -> tuple[list[dict], dict | None]:
    """Phase 2: Create final LLM messages (streamed) including tool results."""
    if outcome.decision.action != "tool_call" or not outcome.tool_payload:
        return llm_messages, None

    tool_name = outcome.tool_payload.get("tool")
    tool_json = json.dumps(outcome.tool_payload, ensure_ascii=False)

    instr = (
        "Du bist ein hilfreicher Assistent. Du erhältst TOOL_RESULT_JSON mit Ergebnissen/Fehlern. "
        "Nutze es für die Antwort. Wenn TOOL_RESULT_JSON einen Fehler enthält, erkläre ihn kurz und nenne die nächste Aktion. "
    )
    if tool_name in ("web_search", "recipe_search"):
        instr += (
            "\nWICHTIG: Du MUSST am Ende eine Quellenliste enthalten. Format:\n"
            "Quellen:\n- <Titel> — <URL>\n- ...\n"
        )

    sys_msg = {
        "role": "system",
        "content": f"{instr}\n\nTOOL_RESULT_JSON:{tool_json}",
    }
    return llm_messages + [sys_msg], outcome.tool_payload