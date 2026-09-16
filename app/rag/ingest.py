"""知识灌库：扫描 data/raw -> MD5 去重（登记簿在 PostgreSQL）
-> 切分 -> DashScope 嵌入 -> 写 knowledge_docs / knowledge_chunks。

用法（项目根目录下）：
    python -m app.rag.ingest
"""
import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session, select

from app.core.config import settings
from app.db.engine import engine
from app.db.models import KnowledgeChunk, KnowledgeDoc

# 中文 Windows 必须显式 utf-8，否则 GBK 读 UTF-8 文件直接崩
ALLOWED_EXT = {".txt", ".pdf"}


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def load_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        pages = PyPDFLoader(str(path)).load()
        return "\n".join(p.page_content for p in pages)
    return TextLoader(str(path), encoding="utf-8").load()[0].page_content


def scan_files() -> list[Path]:
    root = settings.raw_path
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in ALLOWED_EXT)


def main() -> None:
    files = scan_files()
    print(f"[INFO] 资料目录：{settings.raw_path}")
    print(f"[INFO] 扫到 {len(files)} 个文件")

    embedder = DashScopeEmbeddings(model=settings.embedding_model)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )

    ok, skip, fail = 0, 0, 0
    with Session(engine) as session:
        for path in files:
            md5 = file_md5(path)
            exists = session.exec(
                select(KnowledgeDoc).where(KnowledgeDoc.md5 == md5)
            ).first()
            if exists:
                print(f"[SKIP] {path.name} 已入库")
                skip += 1
                continue

            try:
                text = load_file(path)
                if not text.strip():
                    print(f"[WARN] {path.name} 内容为空，跳过")
                    continue

                # 相对 raw 的第一级子目录作为分类，没有子目录则未分类
                rel = path.relative_to(settings.raw_path)
                category = rel.parts[0] if len(rel.parts) > 1 else "未分类"

                chunks = splitter.split_text(text)
                vectors = embedder.embed_documents(chunks)

                doc = KnowledgeDoc(
                    title=path.stem,
                    category=category,
                    source_path=str(path.resolve()),
                    md5=md5,
                    chunk_count=len(chunks),
                )
                # 先 flush 拿到 doc.id，再写切片
                session.add(doc)
                session.flush()

                for i, (content, vec) in enumerate(zip(chunks, vectors)):
                    session.add(KnowledgeChunk(
                        doc_id=doc.id,
                        chunk_index=i,
                        content=content,
                        category=category,
                        embedding=vec,
                    ))
                session.commit()   # 单文件一个事务，失败不污染其他文件
                ok += 1
                print(f"[OK] {path.name} ingested, chunks={len(chunks)}")
            except Exception as e:
                session.rollback()
                fail += 1
                print(f"[FAIL] {path.name}: {e}")

    print(f"[DONE] 新增 {ok}，跳过 {skip}，失败 {fail}")


if __name__ == "__main__":
    main()
