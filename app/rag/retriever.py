"""向量检索封装：query -> 嵌入 -> pgvector 相似度搜索 -> Document 列表。"""
from langchain_core.documents import Document
from langchain_community.embeddings import DashScopeEmbeddings
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.db.engine import engine

_embedder = DashScopeEmbeddings(model=settings.embedding_model)


def retrieve(query: str, k: int = 5) -> list[Document]:
    qvec = _embedder.embed_query(query)
    sql = text("""
        SELECT c.content, c.category, d.title,
               1 - (c.embedding <=> :qvec) AS score
        FROM knowledge_chunks c
        JOIN knowledge_docs d ON d.id = c.doc_id
        ORDER BY c.embedding <=> :qvec
        LIMIT :k
    """)
    with Session(engine) as session:
        rows = session.exec(sql, params={"qvec": str(qvec), "k": k}).all()

    return [
        Document(
            page_content=r.content,
            metadata={"title": r.title, "category": r.category, "score": float(r.score)},
        )
        for r in rows
    ]