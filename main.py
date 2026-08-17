"""
Text2SQL Agent — 命令行交互入口

用法:
    python main.py                    # 默认模式
    python main.py --quiet            # 简洁模式（不打印 ReAct 过程）
    python main.py --question "..."   # 单次查询

启动后输入自然语言问题，Agent 会自动查数据库回答。
输入 quit / exit / q 退出。
"""

import sys
import os

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import AGENT_CONFIG, HARNESS_CONFIG
from core.agent import run
from core.memory import ConversationMemory
from harness import Harness


def load_system_prompt() -> str:
    """加载系统提示词，动态注入数据库结构说明"""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    from core.schema_docs import build_schema_doc
    schema_doc = build_schema_doc()   # 动态生成字段表
    return template.replace("{{TABLE_SCHEMA}}", schema_doc)


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║      🏦 金融数据查询 Agent               ║
║      Text2SQL + DeepSeek + MySQL        ║
║                                          ║
║  输入自然语言问题，Agent 自动查数据库     ║
║  输入 models 查看可用模型                 ║
║  输入 clear 清空对话记忆                  ║
║  输入 verbose / quiet 切换详细模式       ║
║  输入 quit / exit / q 退出               ║
╚══════════════════════════════════════════╝
""")


def list_models():
    """列出当前 API Key 有权调用的所有模型"""
    try:
        from openai import OpenAI
        from core.config import LLM_CONFIG

        client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        models = client.models.list().data
        print(f"\n📋 可用模型（共 {len(models)} 个）:\n")

        for m in models:
            marker = " ★" if m.id == LLM_CONFIG["model"] else ""
            print(f"  {m.id}{marker}")

        print(f"\n★ 标记为当前使用的模型\n")
    except Exception as e:
        print(f"❌ 获取失败: {e}")


def main():
    # 解析命令行参数
    single_question = None
    for arg in sys.argv[1:]:
        if arg == "--quiet" or arg == "-q":
            AGENT_CONFIG["verbose"] = False
        elif arg.startswith("--question="):
            single_question = arg.split("=", 1)[1]

    # 加载系统提示词
    try:
        system_prompt = load_system_prompt()
    except FileNotFoundError:
        print("❌ 找不到 prompts/system.md")
        sys.exit(1)

    # 单次查询模式
    if single_question:
        AGENT_CONFIG["verbose"] = True
        print(f"\n📝 问题: {single_question}\n")
        answer = run(single_question, system_prompt)
        print(f"\n{'─' * 50}")
        print(f"🤖 Agent:\n{answer}")
        return

    # 交互模式
    print_banner()

    # 创建对话记忆
    memory = ConversationMemory(
        max_turns=AGENT_CONFIG.get("memory_max_turns", 10)
    )

    # 创建 Harness（治理层）
    harness = Harness(config=HARNESS_CONFIG, role="viewer")

    print(f"✅ 系统提示词已加载 ({len(system_prompt)} 字符)")
    print(f"✅ Harness: 权限/护栏/脱敏/审计/监控 已启用")
    print(f"✅ 模型: DeepSeek Chat")
    print(f"✅ 详细模式: {'开' if AGENT_CONFIG['verbose'] else '关'}")
    print(f"✅ 最大迭代: {AGENT_CONFIG['max_iterations']} 轮")
    print(f"✅ 对话记忆: {AGENT_CONFIG.get('memory_max_turns', 10)} 轮\n")

    while True:
        try:
            question = input("🔍 请输入查询 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not question:
            continue

        lower = question.lower()
        if lower in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if lower == "verbose":
            AGENT_CONFIG["verbose"] = True
            print("✅ 详细模式已开启")
            continue
        if lower == "quiet":
            AGENT_CONFIG["verbose"] = False
            print("✅ 详细模式已关闭（只显示最终结果）")
            continue
        if lower == "models":
            list_models()
            continue
        if lower == "clear":
            memory.clear()
            print("✅ 对话记忆已清空")
            continue
        if lower == "stats":
            report = harness.monitor.report()
            print(f"\n📊 统计报告:")
            for k, v in report.items():
                print(f"   {k}: {v}")
            print()
            continue

        # 执行 Agent
        answer = run(question, system_prompt, memory, harness=harness, role="admin")

        # 存入记忆
        memory.add_turn(question, answer)

        print(f"\n{'─' * 50}")
        print(f"🤖 Agent:\n{answer}")
        print()


if __name__ == "__main__":
    main()
