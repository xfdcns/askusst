"""问理 AskUSST 服务入口。

启动（项目根目录）：
    python -m uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.agent.service import build_agent
from app.api import auth, chat, feedback, history
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 服务启动时连接 Redis 并建 checkpoint 表；关闭时自动释放
    async with AsyncRedisSaver.from_conn_string(settings.redis_url) as cp:
        await cp.setup()
        app.state.agent = build_agent(cp)
        yield


app = FastAPI(title="问理 AskUSST", lifespan=lifespan)

# 跨域：前端是本地 html / 后续 Vue dev server（5173），都要放行
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 学习/演示用；上线改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(history.router)


@app.get("/")
def root():
    return {"service": "AskUSST", "docs": "/docs"}