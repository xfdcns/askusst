"""数据库引擎与会话工厂。pgvector 的 Vector 类型在 models 里注册。"""
from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,          # 想看 SQL 可临时改成 True
    pool_pre_ping=True,  # 连接池自动剔除失效连接
)


def get_session() -> Session:
    return Session(engine)
