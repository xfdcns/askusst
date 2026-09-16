"""建表 + 建 HNSW 向量索引。

用法（项目根目录下）：
    python -m app.db.init_db
"""
from sqlalchemy import text

from app.db.engine import engine
from app.db.models import SQLModel  # noqa: F401  确保所有表模型已导入注册


def main() -> None:
    # create_all 只建不存在的表，重复执行安全
    SQLModel.metadata.create_all(engine)

    # HNSW：pgvector 的高维近似最近邻索引，查询比顺序扫描快得多
    # 余弦距离操作符 <=>；重复执行会报 already exists，忽略即可
    with engine.begin() as conn:
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
                "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
            ))
        except Exception as e:  # 老版本 pgvector 不支持 HNSW 时退回无索引
            print(f"[WARN] HNSW 索引未建成（不影响灌库，仅检索变慢）：{e}")

    print("[OK] 表和向量索引已就绪。")


if __name__ == "__main__":
    main()
