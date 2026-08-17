"""
Text2SQL Agent — ReAct 循环核心

这是整个项目最重要的文件，实现了：
  Think（思考）→ Act（执行工具）→ Observe（观察结果）→ 循环

和 Dify Agent 节点做的是完全一样的事，但每一行都是透明的。
"""

import json
import time
from .config import AGENT_CONFIG
from .llm import chat
from tools.registry import TOOL_SCHEMAS, execute_tool


def run(user_question: str, system_prompt: str, memory=None, callback=None,
        harness=None, role="admin") -> str:
    """
    执行一次 ReAct 循环，回答用户的数据查询问题。

    参数:
        user_question: 用户的自然语言问题
        system_prompt: 系统提示词（从文件加载）
        memory:       ConversationMemory 实例（可选，用于多轮对话）
        callback:     事件回调函数（可选），每发生一个事件时调用：
                      callback({"type": "tool_call", "name": ..., "args": ...})
                      callback({"type": "tool_result", "preview": ...})
                      callback({"type": "complete", "step": N})
                      callback({"type": "error", "message": ...})
                      Web 端用它把 ReAct 过程推给浏览器；命令行走 print。
        harness:      Harness 实例（可选），提供治理钩子：
                      before_request / before_tool / after_tool / on_complete
        role:         调用者角色（用于权限判断，默认 admin）

    返回:
        Agent 的最终回复文本
    """
    verbose = AGENT_CONFIG["verbose"]
    max_iterations = AGENT_CONFIG["max_iterations"]

    # ============================================================
    # 统一输出：有 callback 走 callback，否则 print（命令行）
    # ============================================================
    def emit(event_type: str, **data):
        if callback:
            callback({"type": event_type, **data})
        elif verbose:
            if event_type == "step":
                print(f"\n{'─' * 50}")
                print(f"🔄 第 {data['step']}/{max_iterations} 轮")
            elif event_type == "tool_call":
                args_preview = json.dumps(data["args"], ensure_ascii=False)
                if len(args_preview) > 120:
                    args_preview = args_preview[:120] + "..."
                print(f"🔧 {data['name']}({args_preview})")
            elif event_type == "tool_result":
                preview = data["preview"]
                print(f"📦 结果: {preview}")
            elif event_type == "complete":
                print(f"✅ Agent 完成，共 {data['step']} 步")

    # ============================================================
    # 挂点 1：请求开始
    # ============================================================
    if harness:
        harness.before_request(role, user_question)

    # ============================================================
    # 初始化对话（注入历史记忆）
    # ============================================================
    history = memory.get_history() if memory else []
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_question},
    ]

    # ============================================================
    # ReAct 循环
    # ============================================================
    for step in range(1, max_iterations + 1):
        emit("step", step=step)

        # ---------- Think + Act：LLM 决定下一步 ----------
        response = chat(messages, tools=TOOL_SCHEMAS)

        # ---------- 情况 1：没有 tool_calls，任务完成 ----------
        if not response.get("tool_calls"):
            emit("complete", step=step)
            # 挂点 4：请求结束
            if harness:
                harness.on_complete(response.get("content", ""))
            return response.get("content", "")

        # ---------- 情况 2：有 tool_calls，逐个执行 ----------
        # 先把 assistant 消息加入对话
        messages.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": response["tool_calls"],
        })

        for tool_call in response["tool_calls"]:
            tool_name = tool_call["function"]["name"]

            # 安全解析参数
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                tool_args = {}

            emit("tool_call", name=tool_name, args=tool_args)

            # ====================================================
            # 挂点 2：工具执行前（可拦截）
            # ====================================================
            if harness:
                block = harness.before_tool(role, tool_name, tool_args)
                if block:
                    # 被拦截：工具不执行，block 作为错误结果
                    result_str = json.dumps(block, ensure_ascii=False)
                else:
                    # ---------- Observe：真正执行工具 ----------
                    result_str = execute_tool(tool_name, tool_args)
            else:
                result_str = execute_tool(tool_name, tool_args)

            # ====================================================
            # 挂点 3：工具执行后（可修改结果）
            # ====================================================
            if harness:
                result_str = harness.after_tool(tool_name, result_str)

            # 结果预览（callback 和 print 共用）
            preview = result_str[:150].replace("\n", " ")
            if len(result_str) > 150:
                preview += "..."
            emit("tool_result", preview=preview)

            # 把工具结果塞回对话
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result_str,
            })

    # 达到最大迭代次数
    emit("error", message=f"达到最大迭代次数 ({max_iterations})")

    # 最后一次，不加 tools 让它给最终回复
    messages.append({
        "role": "user",
        "content": "你已经达到了最大工具调用次数。请基于已有的信息，直接给出你的最佳回答。"
    })
    final = chat(messages, tools=None)
    return final.get("content", "抱歉，未能完成查询。")
