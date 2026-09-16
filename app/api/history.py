"""历史会话接口（第5周）。
- GET  /conversations        某用户的会话列表（左侧栏）
- GET  /conversations/{id}/messages   某会话的消息流水（点开看全文）
"""
from fastapi import APIRouter, Header, HTTPException
from sqlmodel import Session, select

from app.db.engine import engine
from app.db.models import ChatMessage, Conversation, User

router = APIRouter(tags=["history"])


@router.get("/conversations")
def list_conversations(x_user_id: int = Header(alias="X-User-Id")):
    with Session(engine) as s:
        if not s.get(User, x_user_id):
            raise HTTPException(401, "用户不存在，请先登录")
        convs = s.exec(
            select(Conversation)
            .where(Conversation.user_id == x_user_id)
            .order_by(Conversation.id.desc())
        ).all()
        return [
            {"conversation_id": c.id, "title": c.title or "未命名会话",
             "created_at": c.created_at.isoformat(timespec="seconds")}
            for c in convs
        ]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int,
                  x_user_id: int = Header(alias="X-User-Id")):
    with Session(engine) as s:
        if not s.get(User, x_user_id):
            raise HTTPException(401, "用户不存在，请先登录")
        conv = s.get(Conversation, conversation_id)
        if not conv or conv.user_id != x_user_id:
            raise HTTPException(403, "无权访问该会话")
        msgs = s.exec(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id)
        ).all()
        return [
            {"role": m.role, "content": m.content,
             "created_at": m.created_at.isoformat(timespec="seconds")}
            for m in msgs
        ]
