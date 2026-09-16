"""全部数据表。本周实际用到 knowledge_docs / knowledge_chunks，
其余表先建好，第 3~4 周登录、记忆、反馈直接用。"""
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.core.config import settings


# ── 业务表 ──────────────────────────────────────────────
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(index=True, unique=True, max_length=32)
    nickname: str = ""
    college: str = ""
    major: str = ""
    grade: str = ""
    role: str = "student"          # student / admin
    created_at: datetime = Field(default_factory=datetime.now)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    thread_id: str = Field(index=True, unique=True, max_length=128)
    title: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatMessage(SQLModel, table=True):
    """消息流水（第5周）：业务侧长期留存，用于历史会话展示；
    Agent 的短期上下文仍由 Redis checkpointer 管，两边各管一事。"""
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str = Field(max_length=16)       # user / assistant
    content: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.now)


class UserFact(SQLModel, table=True):
    """长期记忆：从对话里抽出的用户事实，按 user_id 隔离。"""
    __tablename__ = "user_facts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    fact_key: str = Field(max_length=64)
    fact_value: str = Field(max_length=512)
    source_msg_id: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.now)


# ── RAG 知识库表 ──
class KnowledgeDoc(SQLModel, table=True):
    """文档台账：md5 唯一约束实现文件级去重。"""
    __tablename__ = "knowledge_docs"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=256)
    category: str = Field(default="未分类", index=True, max_length=64)
    source_path: str = ""
    source_url: str = ""
    md5: str = Field(index=True, unique=True, max_length=32)
    version: int = 1
    status: str = "active"
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class KnowledgeChunk(SQLModel, table=True):
    """知识切片 + 向量。embedding 维度要与所用 embedding 模型一致。"""
    __tablename__ = "knowledge_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    doc_id: int = Field(foreign_key="knowledge_docs.id", index=True)
    chunk_index: int = 0
    content: str = Field(sa_column=Column(Text, nullable=False))
    category: str = Field(default="未分类", index=True, max_length=64)
    # 关键：pgvector 向量列（text-embedding-v3 默认 1024 维）
    embedding: list[float] = Field(
        sa_column=Column(Vector(settings.embedding_dim))
    )
    created_at: datetime = Field(default_factory=datetime.now)


class Feedback(SQLModel, table=True):
    """点赞点踩：第 4 周上线，后续做评测/论文数据用。"""
    __tablename__ = "feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversations.id")
    question: str = Field(sa_column=Column(Text))
    answer: str = Field(sa_column=Column(Text))
    rating: str = Field(max_length=8)       # up / down
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
