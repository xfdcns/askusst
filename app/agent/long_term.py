"""长期记忆

机制：
1. 每轮对话结束后，用 LLM 从"用户消息 + 助手回答"里抽取结构化事实
   （专业、年级、校区、偏好……），存进 user_facts 表，按 user_id 隔离；
2. 每个新会话的第一条消息前，把该用户的全部事实注入一条 system 消息，
   Agent 因此能跨会话"记住"用户，但学校规定仍以 ask_knowledge 检索为准。

"""
import json

from langchain_community.chat_models import ChatTongyi
from sqlmodel import Session, select

from app.core.config import settings
from app.db.engine import engine
from app.db.models import UserFact

llm = ChatTongyi(model_name=settings.chat_model, temperature=0)

EXTRACT_PROMPT = """你是信息抽取器。从下面这轮师生对话中，抽取"关于该学生本人"的长期稳定事实。

只抽取：专业、年级/入学年份、学院、校区、学号、明确的学习偏好或目标（如"准备考研""想转码"）。
不要抽取：一次性问题、学校公共信息、课程客观内容、寒暄。
对话里没有就返回空列表。不要臆测。

只输出 JSON 数组，每个元素 {"key": 英文短键, "value": 中文值}，例如：
[{"key": "major", "value": "计算机技术"}, {"key": "campus", "value": "军工路校区"}]

用户消息：{user}
助手回答：{assistant}
JSON："""


def load_facts(user_id: int) -> dict[str, str]:
    """读出某用户的全部长期事实 {fact_key: fact_value}。"""
    with Session(engine) as s:
        rows = s.exec(
            select(UserFact).where(UserFact.user_id == user_id)
        ).all()
        return {r.fact_key: r.fact_value for r in rows}


def build_memory_message(user_id: int):
    """新会话首条消息前注入；没有事实则返回 None（不注入）。"""
    facts = load_facts(user_id)
    if not facts:
        return None
    lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
    return ("system",
            "以下是系统记录的该学生长期信息，用于个性化称呼与理解语境，"
            "但涉及学校规定、课程学分等客观事实时仍必须以 ask_knowledge 工具返回为准：\n"
            + lines)


def _parse_json_list(text: str) -> list[dict]:
    """容错解析：截取第一个 [ 到最后一个 ]，模型偶尔会带 markdown 代码块。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("["), text.rfind("]")
        if i == -1 or j == -1 or j < i:
            return []
        try:
            data = json.loads(text[i:j + 1])
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def extract_and_save(user_id: int, user_message: str, assistant_answer: str) -> int:
    """一轮对话后调用：抽事实并按 (user_id, fact_key) upsert。返回新增/更新条数。"""
    prompt = EXTRACT_PROMPT.replace("{user}", user_message) \
                          .replace("{assistant}", assistant_answer)
    raw = llm.invoke(prompt).content
    items = _parse_json_list(raw if isinstance(raw, str) else "")

    changed = 0
    with Session(engine) as s:
        existing = {
            r.fact_key: r
            for r in s.exec(select(UserFact).where(UserFact.user_id == user_id)).all()
        }
        for item in items:
            key = str(item.get("key", "")).strip()[:64]
            value = str(item.get("value", "")).strip()[:512]
            if not key or not value:
                continue
            row = existing.get(key)
            if row is None:
                s.add(UserFact(user_id=user_id, fact_key=key, fact_value=value))
                changed += 1
            elif row.fact_value != value:
                row.fact_value = value
                s.add(row)
                changed += 1
        if changed:
            s.commit()
    return changed
