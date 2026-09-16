"""前台直接跑一次长期记忆抽取，报错会直接显示在终端。"""
from app.agent.long_term import extract_and_save, load_facts

n = extract_and_save(
    1,
    "我是2025级计算机技术专业的研究生，在军工路校区",
    "好的，已了解你的情况，有问题随时问我。",
)
print("抽取条数：", n)
print("当前事实：", load_facts(1))