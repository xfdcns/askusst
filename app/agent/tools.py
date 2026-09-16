"""Agent 可调用的工具集。
- ask_knowledge：校园知识库 RAG
- get_file：当学生明确需要"表格/文件/表单/原图/文档原件"等资料时，
  在资料文件库中定位文件并返回"文件卡片"（JSON）。工具不回传二进制，
  真正的文件由服务层通过 /files/download 链接随 SSE 发给学生。
"""
import json

from langchain_core.tools import tool

from app.agent.file_store import search_files
from app.rag.qa import answer


@tool
def ask_knowledge(query: str) -> str:
    """查询上海理工大学的培养方案、课程、学分学时、教务制度、校园生活等官方资料。
    凡是涉及学校具体规定、课程信息的问题，都必须调用本工具，并以工具返回为准。
    参数 query：凝练后的核心检索词，如"高等数学A 学分"。"""
    result, _ = answer(query)
    return result


@tool
def get_file(query: str) -> str:
    """当学生需要下载/获取"文件、表格、表单、文档原件、Excel、PDF、图片"时调用本工具，
    例如"给我培养计划表""发一份转专业申请表""有没有校历 Excel""把那张流程图发我"。
    本工具只负责按描述找到对应资料；纯文字知识性提问（某课多少学分）请改用 ask_knowledge。
    参数 query：学生想要的文件描述或文件名关键词，如"2025 本科培养计划表"。
    返回：JSON。命中时含 files 列表（每项有 file_id/name/type/ext/size/desc，供你知道找到了什么；
    注意：结果里【不含】下载链接，文件卡片由系统自动发送给学生，你无需也禁止输出任何链接），
    未命中返回 {"files": [], "message": "..."}，此时应如实告知并建议联系教务处。"""
    hits = search_files(query, top_k=3)
    if not hits:
        return json.dumps({
            "files": [],
            "message": "资料文件库中未找到匹配文件，不要编造文件，建议学生咨询教务处或辅导员。",
        }, ensure_ascii=False)

    cards = []
    for h in hits:
        cards.append({
            "file_id": h["file_id"],
            "name": h["name"],
            "type": h["type"],
            "ext": h["ext"],
            "size": h["size"],
            "desc": h.get("desc", ""),
        })
    return json.dumps({"files": cards}, ensure_ascii=False)


TOOLS = [ask_knowledge, get_file]
