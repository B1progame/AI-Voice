from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from backend.app.core.security import require_csrf_for_unsafe_methods
from backend.app.db.session import SessionLocal
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message, MessageRole
from backend.app.models.user import User, UserRole
from backend.app.routers.me import current_user_dep
from backend.app.schemas.conversation import ConversationOut, ConversationCreateIn, ConversationPatchIn
from backend.app.schemas.message import MessageOut, MessageCreateIn
from backend.app.services.chat_service import stream_assistant_reply

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_conversation_for_user(db: Session, *, conv_id: int, user: User) -> Conversation:
    conv = db.execute(select(Conversation).where(Conversation.id == conv_id)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user.role != UserRole.admin and conv.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    q = select(Conversation).order_by(Conversation.updated_at.desc())
    if user.role != UserRole.admin:
        q = q.where(Conversation.user_id == user.id)

    rows = db.execute(q).scalars().all()
    return [
        ConversationOut(
            id=c.id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in rows
    ]


@router.post("", response_model=ConversationOut)
def create_conversation(payload: ConversationCreateIn, request: Request, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    require_csrf_for_unsafe_methods(request)

    conv = Conversation(user_id=user.id, title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationOut(id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at)


@router.patch("/{conv_id}", response_model=ConversationOut)
def rename_conversation(conv_id: int, payload: ConversationPatchIn, request: Request, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    require_csrf_for_unsafe_methods(request)
    conv = get_conversation_for_user(db, conv_id=conv_id, user=user)

    conv.title = payload.title
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationOut(id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at)


@router.delete("/{conv_id}")
def delete_conversation(conv_id: int, request: Request, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    require_csrf_for_unsafe_methods(request)
    conv = get_conversation_for_user(db, conv_id=conv_id, user=user)

    db.delete(conv)
    db.commit()
    return {"ok": True}


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
def list_messages(conv_id: int, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    conv = get_conversation_for_user(db, conv_id=conv_id, user=user)
    rows = db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.asc())
    ).scalars().all()

    return [
        MessageOut(id=m.id, role=m.role.value, content=m.content, created_at=m.created_at)
        for m in rows
    ]


@router.post("/{conv_id}/messages", response_model=MessageOut)
def create_user_message(conv_id: int, payload: MessageCreateIn, request: Request, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    require_csrf_for_unsafe_methods(request)
    conv = get_conversation_for_user(db, conv_id=conv_id, user=user)

    msg = Message(conversation_id=conv.id, role=MessageRole.user, content=payload.content)
    db.add(msg)

    # Update conversation timestamp
    conv.updated_at = msg.created_at
    db.add(conv)

    db.commit()
    db.refresh(msg)
    return MessageOut(id=msg.id, role=msg.role.value, content=msg.content, created_at=msg.created_at)


def _sse_event(event: str, data: str) -> str:
    # SSE format: event + data lines + blank line
    safe_data = data.replace("\r", "")
    return f"event: {event}\ndata: {safe_data}\n\n"


@router.get("/{conv_id}/stream")
async def stream_assistant(conv_id: int, request: Request, user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    """
    SSE endpoint: streams assistant reply for the conversation.

    Safety/robustness:
    - Requires last message to be a user message.
    - Prevents duplicate responses: if an assistant message exists after the last user message, returns 409.
    """
    conv = get_conversation_for_user(db, conv_id=conv_id, user=user)

    # Find last message
    last = db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(1)
    ).scalar_one_or_none()

    if not last:
        raise HTTPException(status_code=400, detail="No messages in conversation yet")

    if last.role != MessageRole.user:
        raise HTTPException(status_code=409, detail="Last message is not a user message (already answered?)")

    # Duplicate prevention: check if any assistant message has higher id than the last user msg
    existing_after = db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .where(Message.id > last.id)
        .where(Message.role == MessageRole.assistant)
        .limit(1)
    ).scalar_one_or_none()
    if existing_after:
        raise HTTPException(status_code=409, detail="Assistant reply already exists for latest user message")

    async def event_generator() -> AsyncIterator[str]:
        # Keepalive pings so proxies don’t close the connection
        yield _sse_event("start", "ok")

        assistant_accum: list[str] = []
        last_ping = asyncio.get_event_loop().time()

        try:
            async for token in stream_assistant_reply(db, conversation_id=conv.id):
                assistant_accum.append(token)
                yield _sse_event("token", token)

                now = asyncio.get_event_loop().time()
                if now - last_ping > 10.0:
                    yield _sse_event("ping", "keepalive")
                    last_ping = now

                # If client disconnected, stop work
                if await request.is_disconnected():
                    return

            full_text = "".join(assistant_accum).strip()
            if not full_text:
                full_text = "(No output from model)"

            # Persist assistant message
            m = Message(conversation_id=conv.id, role=MessageRole.assistant, content=full_text)
            db.add(m)
            conv.updated_at = m.created_at
            db.add(conv)
            db.commit()

            yield _sse_event("done", "ok")
        except Exception as e:
            # Log server-side; send error to client
            yield _sse_event("error", f"{type(e).__name__}: {str(e)}")

    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "text/event-stream",
        "Connection": "keep-alive",
        # Helps with some proxies; harmless otherwise
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers, media_type="text/event-stream")