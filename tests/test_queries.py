"""
Text2SQL Agent — 测试用例集

用法:
    python test_queries.py

对每个测试问题执行一次 Agent 查询，输出结果和耗时。
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import run
from core.schema_docs import build_schema_doc

# 加载系统提示词（动态注入数据库结构说明）
PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "system.md"
)
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    _template = f.read()
SYSTEM_PROMPT = _template.replace("{{TABLE_SCHEMA}}", build_schema_doc())

# 关闭详细模式，只输出结果
from core.config import AGENT_CONFIG
AGENT_CONFIG["verbose"] = False

# ============================================================
# 测试用例
# ============================================================
TEST_QUERIES = [
    # --- 基础查询 ---
    ("基础", "数据库里有哪些表？"),
    ("基础", "customer 表有哪些字段？"),

    # --- 业务查询 ---
    ("业务", "7月交易金额最高的5笔是什么？"),
    ("业务", "张三买了哪些产品？"),
    ("业务", "按客户风险等级分组，统计每个等级的客户数量"),

    # --- 数据质量 ---
    ("质量", "有多少客户没有填写证件有效期？"),
    ("质量", "姓名里有特殊字符的客户有哪些？"),
    ("质量", "手机号格式不正确的客户有多少？"),
    ("质量", "有没有客户的证件有效期已经过了？"),

    # --- 关联查询 ---
    ("关联", "余额最高的5个账户分别属于哪些客户？"),
    ("关联", "交易金额超过10万的交易，对应的客户名和交易对手是什么？"),
    ("关联", "每个产品的持有客户数是多少？"),

    # --- 混合查询 ---
    ("混合", "没有填证件有效期的客户中，有没有仍在交易的？"),
    ("混合", "手机号异常的客户在7月有没有大额交易？"),
]


def main():
    total = len(TEST_QUERIES)
    passed = 0

    print(f"\n{'=' * 60}")
    print(f"  Text2SQL Agent 测试集 — 共 {total} 题")
    print(f"{'=' * 60}")

    for i, (category, question) in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{total}] [{category}] {question}")
        print("-" * 50)

        start = time.time()
        try:
            answer = run(question, SYSTEM_PROMPT)
            elapsed = time.time() - start
            # 简单判定：有内容且没有报错
            if answer and len(answer) > 20:
                print(f"✅ 通过 ({elapsed:.1f}s)")
                # 只打印前 200 字
                preview = answer[:200].replace("\n", " ")
                print(f"   {preview}...")
                passed += 1
            else:
                print(f"⚠️ 答案过短 ({elapsed:.1f}s)")
                print(f"   {answer}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ 异常 ({elapsed:.1f}s): {e}")

    print(f"\n{'=' * 60}")
    print(f"  结果: {passed}/{total} 通过")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
