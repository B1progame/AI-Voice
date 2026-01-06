import json
from datetime import datetime
from typing import Generator, Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging_setup import get_logger
from backend.core.security import decode_access_token
from backend.db.database import get_db
from backend.db.models import User, Conversation, Message
from backend.db.settings_crud import get_admin_settings  # <--- NEW IMPORT
from backend.schemas.conversations import (
    ConversationCreateIn,
    ConversationRenameIn,
    MessageCreateIn,
)
from backend.services.ollama import stream_chat_completion
from backend.services.tool_orchestrator import plan_action, run_planned_tool, build_final_messages
from backend.services.tools.context import ToolContext

LOG = get_logger(__name__)
router = APIRouter(tags=["conversations"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", "0"))
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if user.status != "approved":
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


def _require_owner_or_admin(conv: Conversation, user: User) -> bool:
    return user.role == "admin" or conv.user_id == user.id


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Conversation)
    if user.role != "admin":
        q = q.filter(Conversation.user_id == user.id)
    convs = q.order_by(Conversation.updated_at.desc()).all()
    return {
        "ok": True,
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ],
    }


@router.post("/conversations")
def create_conversation(payload: ConversationCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    title = (payload.title or "New Chat").strip()[:200]
    conv = Conversation(user_id=user.id, title=title, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(conv)
    db.commit()
    return {"ok": True, "conversation": {"id": conv.id, "title": conv.title}}


@router.patch("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    payload: ConversationRenameIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
    if not _require_owner_or_admin(conv, user):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    conv.title = payload.title.strip()[:200]
    conv.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
    if not _require_owner_or_admin(conv, user):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    db.delete(conv)
    db.commit()
    return {"ok": True}


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
    if not _require_owner_or_admin(conv, user):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    msgs = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return {
        "ok": True,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.post("/conversations/{conversation_id}/messages")
def create_message(
    conversation_id: int,
    payload: MessageCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
    if not _require_owner_or_admin(conv, user):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    if payload.role != "user":
        return JSONResponse(status_code=400, content={"detail": "Only user messages can be created via this endpoint"})

    msg = Message(
        conversation_id=conversation_id,
        user_id=user.id,
        role="user",
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "message": {"id": msg.id}}


def _sse(data: dict, event: Optional[str] = None) -> str:
    s = ""
    if event:
        s += f"event: {event}\n"
    s += f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    return s


@router.get("/conversations/{conversation_id}/stream")
def stream_assistant(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
    if not _require_owner_or_admin(conv, user):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.LLM_MAX_CONTEXT_MESSAGES)
        .all()
    )
    msgs = list(reversed(msgs))

    if not msgs or msgs[-1].role != "user":
        return JSONResponse(
            status_code=400,
            content={"detail": "Last message must be a user message. Send a user message first."},
        )

    llm_messages = []
    
    # --- START SYSTEM CONTEXT INJECTION ---
    # 1. Load Admin Settings to get Location
    settings_row = get_admin_settings(db)
    
    # 2. Format Date and Location
    current_time = datetime.now().strftime("%A, %d. %B %Y %H:%M")
    location_name = settings_row.default_location_name or "Unknown Location"
    
    # 3. Build the System Prompt
    system_context = (
        f"Current time: {current_time}. "
        f"Current location: {location_name}. "
        "If the user asks for weather without a city, use the current location."
    )
    
    # 4. Insert as the very first message
    llm_messages.append({
        "role": "system", 
        "content": f"You are a helpful AI assistant. {system_context}"
    })
    # --- END SYSTEM CONTEXT INJECTION ---

    for m in msgs:
        if m.role not in ("user", "assistant", "system"):
            continue
        llm_messages.append({"role": m.role, "content": m.content})

    # Stage 1.5: Planner + optional tool execution
    ctx = ToolContext(db=db, user=user)
    decision = plan_action(llm_messages)
    outcome = run_planned_tool(decision, ctx)
    final_llm_messages, tool_payload = build_final_messages(llm_messages, outcome)
    used_tool = (tool_payload or {}).get("tool") if tool_payload else None

    def event_generator() -> Generator[str, None, None]:
        assistant_text_parts: list[str] = []
        try:
            yield _sse({"ok": True, "message": "stream_started"}, event="meta")

            for token in stream_chat_completion(final_llm_messages):
                assistant_text_parts.append(token)
                yield _sse({"token": token}, event="token")

            full = "".join(assistant_text_parts).strip()
            if not full:
                full = "(Empty response)"

            # Enforce sources for search-based tools even if the model forgets.
            if used_tool in ("web_search", "recipe_search"):
                if "http" not in full and "Quellen" not in full:
                    try:
                        results = ((tool_payload or {}).get("result") or {}).get("results") or []
                        if results:
                            extra_lines = ["\n\nQuellen:"]
                            for r in results[:5]:
                                title = (r.get("title") or "").strip()
                                url = (r.get("url") or "").strip()
                                if title or url:
                                    extra_lines.append(f"- {title} — {url}")
                            extra = "\n".join(extra_lines)
                            full += extra
                            yield _sse({"token": extra}, event="token")
                    except Exception:
                        pass

            m = Message(
                conversation_id=conversation_id,
                user_id=None,
                role="assistant",
                content=full,
                created_at=datetime.utcnow(),
            )
            db.add(m)
            conv.updated_at = datetime.utcnow()
            db.commit()

            yield _sse({"ok": True, "assistant_message_id": m.id}, event="done")
        except GeneratorExit:
            partial = "".join(assistant_text_parts).strip()
            if partial:
                m = Message(
                    conversation_id=conversation_id,
                    user_id=None,
                    role="assistant",
                    content=partial,
                    created_at=datetime.utcnow(),
                )
                db.add(m)
                conv.updated_at = datetime.utcnow()
                db.commit()
            return
        except Exception as e:
            LOG.exception("Streaming failed: %s", e)
            yield _sse({"ok": False, "detail": "LLM streaming failed"}, event="error")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)