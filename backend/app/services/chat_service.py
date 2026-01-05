from __future__ import annotations

import logging
from typing import AsyncIterator, List, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.message import Message, MessageRole
from backend.app.services.ollama_client import ollama_client

logger = logging.getLogger(__name__)


def build_ollama_messages(db: Session, *, conversation_id: int) -> List[Dict[str, str]]:
    # System prompt first
    msgs: List[Dict[str, str]] = [{"role": "system", "content": settings.system_prompt}]

    rows = db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    ).scalars().all()

    for m in rows:
        if m.role == MessageRole.system:
            # not used in MVP; keep support
            msgs.append({"role": "system", "content": m.content})
        elif m.role == MessageRole.user:
            msgs.append({"role": "user", "content": m.content})
        elif m.role == MessageRole.assistant:
            msgs.append({"role": "assistant", "content": m.content})

    return msgs


async def stream_assistant_reply(db: Session, *, conversation_id: int) -> AsyncIterator[str]:
    messages = build_ollama_messages(db, conversation_id=conversation_id)

    async for token in ollama_client.stream_chat(model=settings.ollama_model, messages=messages):
        yield token