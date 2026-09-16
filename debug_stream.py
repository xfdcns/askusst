"""诊断：打印每个流式片的节点名、消息类型、内容前80字。"""
import asyncio

from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.agent.service import build_agent
from app.core.config import settings


async def main():
    async with AsyncRedisSaver.from_conn_string(settings.redis_url) as cp:
        await cp.setup()
        agent = build_agent(cp)
        async for msg, meta in agent.astream(
            {"messages": [("user", "高等数学A(1)几个学分？")]},
            config={"configurable": {"thread_id": "debug-1"}},
            stream_mode="messages",
        ):
            print(f"[{meta.get('langgraph_node')}] "
                  f"{type(msg).__name__} -> {repr(msg.content)[:80]}")


asyncio.run(main())