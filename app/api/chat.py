"""流式问答接口（第4周版）。
- header X-User-Id：登录拿到的 user_id
- body.conversation_id 不传 = 开新会话；传了 = 在同一会话内多轮（短期记忆生效）
- 新会话首条消息前注入该用户的长期记忆（user_facts）
- 流结束后后台异步抽取长期事实，不阻塞响应
"""
import asyncio
import json
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import ToolMessage
from pydantic import BaseModel
from sqlmodel import Session

from app.agent.long_term import build_memory_message, extract_and_save
from app.db.engine import engine
from app.db.models import ChatMessage, Conversation, User

router = APIRouter(tags=["chat"])

# 持有后台抽取任务的引用，防止事件循环里的任务被 GC（FastAPI 后台任务的标准写法）
_bg_tasks: set[asyncio.Task] = set()


class ChatIn(BaseModel):
    message: str
    conversation_id: int | None = None


def _resolve_session(user_id: int, conversation_id: int | None, first_msg: str):
    """返回 (conversation_id, thread_id, is_new)，并校验会话归属。"""
    with Session(engine) as s:
        if not s.get(User, user_id):
            raise HTTPException(401, "用户不存在，请先登录")

        if conversation_id:
            conv = s.get(Conversation, conversation_id)
            if not conv or conv.user_id != user_id:
                raise HTTPException(403, "无权访问该会话")
            return conv.id, conv.thread_id, False

        thread_id = f"u{user_id}-{uuid.uuid4().hex[:12]}"
        conv = Conversation(user_id=user_id, thread_id=thread_id,
                            title=first_msg[:20])
        s.add(conv)
        s.commit()
        s.refresh(conv)
        return conv.id, conv.thread_id, True


@router.post("/chat")
async def chat(req: Request, body: ChatIn,
               x_user_id: int = Header(alias="X-User-Id")):
    agent = req.app.state.agent
    conversation_id, thread_id, is_new = _resolve_session(
        x_user_id, body.conversation_id, body.message)

    # 用户消息落库（业务留存）
    with Session(engine) as s:
        s.add(ChatMessage(conversation_id=conversation_id,
                          role="user", content=body.message))
        s.commit()

    # 新会话：长期记忆注入到消息序列最前面（作为 system 消息）
    messages = []
    if is_new:
        mem = build_memory_message(x_user_id)
        if mem:
            messages.append(mem)
    messages.append(("user", body.message))

    async def event_stream():
        # 先把新会话 id 发给前端
        yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

        answer_parts: list[str] = []
        sent_files: list[dict] = []
        seen_ids: set[str] = set()

        # stream_mode="messages"：模型每吐一个字就 yield 一次
        async for msg, meta in agent.astream(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        ):
            # 工具节点产出：截获 get_file 返回的文件卡片，单独推 file 事件（不进正文）
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str) \
                    and '"files"' in msg.content:
                try:
                    payload = json.loads(msg.content)
                except json.JSONDecodeError:
                    payload = {}
                for f in payload.get("files", []):
                    fid = str(f.get("file_id", ""))
                    if not fid or fid in seen_ids:
                        continue
                    seen_ids.add(fid)
                    card = {
                        "file_id": fid,
                        "name": f.get("name", fid),
                        "type": f.get("type", "file"),
                        "ext": f.get("ext", ""),
                        "size": f.get("size", 0),
                        "desc": f.get("desc", ""),
                        "url": f.get("download_url")
                               or f"/files/download?file_id={fid}",
                    }
                    sent_files.append(card)
                    yield f"event: file\ndata: {json.dumps(card, ensure_ascii=False)}\n\n"
                continue

            # 只转发"模型节点"产出的文字；工具调用过程不发给用户
            # 注意：langchain 1.x create_agent 的模型节点名是 "model" 不是 "agent"
            if meta.get("langgraph_node") == "model" \
                    and isinstance(msg.content, str) and msg.content:
                answer_parts.append(msg.content)
                yield f"data: {json.dumps(msg.content, ensure_ascii=False)}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

        # 流结束后：助手回复落库，再后台抽取长期事实（LLM 调用放线程池，不阻塞事件循环）
        full_answer = "".join(answer_parts)
        if sent_files:
            att = "\n".join(f"[附件] {f['name']}" for f in sent_files)
            full_answer = (full_answer + "\n" + att).strip()
        if full_answer.strip():
            with Session(engine) as s:
                s.add(ChatMessage(conversation_id=conversation_id,
                                  role="assistant", content=full_answer))
                s.commit()
            task = asyncio.create_task(asyncio.to_thread(
                extract_and_save, x_user_id, body.message, full_answer))
            _bg_tasks.add(task)

            def _on_done(t: asyncio.Task):
                _bg_tasks.discard(t)
                if t.exception():
                    print(f"[long-term] 抽取失败：{t.exception()!r}")

            task.add_done_callback(_on_done)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
