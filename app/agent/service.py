"""Agent 工厂：qwen-plus + 工具 + 短期记忆 checkpointer。"""
from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi

from app.agent.tools import TOOLS
from app.core.config import settings

SYSTEM_PROMPT = """你是"问理 AskUSST"，上海理工大学的校园问答助手。
规则：
1. 凡涉及课程、培养方案、学分、教务制度等学校信息，必须先调用 ask_knowledge 工具，严格基于工具返回回答，禁止编造；
2. 2. 工具返回中没有的信息一律视为"不知道"：禁止补充任何资料外的电话、邮箱、网址、日期、数字，
   被用户质疑来源时直接承认无依据，严禁用常识"核实"后再给出新联系方式；
3. 天气、气温类问题调用 get_weather 工具；
4. 用中文简洁分点作答，数字（课程代码/学分/学时）原样引用；
5. 打招呼、闲聊等不涉及学校信息的问题可直接友好回复。"""


def build_agent(checkpointer):
    llm = ChatTongyi(model_name=settings.chat_model, streaming=True)
    return create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,   # 短期记忆：按 thread_id 自动存取
    )
