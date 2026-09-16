"""第二周：RAG 问答闭环（检索 -> 拼资料 -> qwen-plus 生成）。

用法（项目根目录）：
    python -m app.rag.qa
"""
from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.core.config import BASE_DIR, settings
from app.rag.retriever import retrieve

prompt_text = (BASE_DIR / "prompts" / "rag_prompt.txt").read_text(encoding="utf-8")
prompt = PromptTemplate.from_template(prompt_text)
llm = ChatTongyi(model_name=settings.chat_model)
chain = prompt | llm | StrOutputParser()


def answer(question: str) -> tuple[str, list]:
    docs = retrieve(question, k=5)
    context = "\n\n".join(
        f"[资料{i}] 来源：《{d.metadata['title']}》\n{d.page_content}"
        for i, d in enumerate(docs, 1)
    )
    result = chain.invoke({"input": question, "context": context})
    return result, docs


if __name__ == "__main__":
    print("问理 AskUSST｜输入 q 退出")
    while True:
        question = input("\n你的问题：").strip()
        if not question:
            continue
        if question.lower() == "q":
            break
        result, docs = answer(question)
        print("\n" + result)
        print(f"\n（参考了 {len(docs)} 个切片，最高相关度 {docs[0].metadata['score']:.3f}）")