"""第一周验收：纯向量相似度检索（还没有 LLM 生成，先确认检索质量）。

用法（项目根目录下）：
    python -m app.rag.search_test 保研绩点怎么算
"""
import sys

from langchain_community.embeddings import DashScopeEmbeddings
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.db.engine import engine

TOP_K = 5


def search(query: str, k: int = TOP_K) -> None:
    embedder = DashScopeEmbeddings(model=settings.embedding_model)
    qvec = embedder.embed_query(query)

    # pgvector 余弦距离 <=> ：距离越小越相似，score = 1 - distance（约 -1~1）
    sql = text("""
        SELECT c.chunk_index,
               c.content,
               c.category,
               d.title,
               1 - (c.embedding <=> :qvec) AS score
        FROM knowledge_chunks c
        JOIN knowledge_docs d ON d.id = c.doc_id
        ORDER BY c.embedding <=> :qvec
        LIMIT :k
    """)

    with Session(engine) as session:
        rows = session.exec(sql, params={"qvec": str(qvec), "k": k}).all()

    print(f"\n查询：{query}\n" + "=" * 60)
    for i, r in enumerate(rows, 1):
        snippet = r.content.replace("\n", " ")[:150]
        print(f"{i}. [score={r.score:.4f}] 《{r.title}》 分类:{r.category}")
        print(f"   {snippet}\n")
    if not rows:
        print("没搜到任何内容——先跑 python -m app.rag.ingest 灌库。")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "保研绩点怎么算"
    search(q)
