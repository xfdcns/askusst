"""Agent 可调用的工具集。
- ask_knowledge：校园知识库 RAG（第2周）
- get_weather：高德开放平台实时天气（第4周，演示第三方 API 工具封装）
"""
import requests
from langchain_core.tools import tool

from app.core.config import settings
from app.rag.qa import answer


@tool
def ask_knowledge(query: str) -> str:
    """查询上海理工大学的培养方案、课程、学分学时、教务制度、校园生活等官方资料。
    凡是涉及学校具体规定、课程信息的问题，都必须调用本工具，并以工具返回为准。
    参数 query：凝练后的核心检索词，如"高等数学A 学分"。"""
    result, _ = answer(query)
    return result


@tool
def get_weather(city: str = "上海") -> str:
    """查询某城市的实时天气（温度、天气现象、风向风力、湿度）。
    用户问天气、气温、要不要带伞时调用。默认城市为上海。
    参数 city：城市名，如"上海""北京"。"""
    key = settings.amap_key
    if not key or key.startswith("在此填入"):
        return "天气服务尚未配置：请在高德开放平台申请 Web 服务 Key，填入 .env 的 AMAP_KEY。"

    try:
        # 第一步：城市名 -> adcode（高德区划编码）
        geo = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": key, "address": city},
            timeout=8,
        ).json()
        if geo.get("status") != "1" or not geo.get("geocodes"):
            return f"未找到城市：{city}"
        adcode = geo["geocodes"][0]["adcode"]
        city_name = geo["geocodes"][0].get("city") or geo["geocodes"][0].get("formatted_address", city)

        # 第二步：按 adcode 查实时天气
        wt = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={"key": key, "city": adcode, "extensions": "base"},
            timeout=8,
        ).json()
        if wt.get("status") != "1" or not wt.get("lives"):
            return f"{city} 天气查询失败"
        live = wt["lives"][0]
        return (f"{live.get('province', '')}{live.get('city', city_name)} "
                f"{live.get('weather')}，气温 {live.get('temperature')}℃，"
                f"{live.get('winddirection')}风 {live.get('windpower')} 级，"
                f"湿度 {live.get('humidity')}%，数据更新时间 {live.get('reporttime')}")
    except requests.RequestException as e:
        return f"天气接口请求异常：{e}"


TOOLS = [ask_knowledge, get_weather]
