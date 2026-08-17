"""
LLM 封装 — DeepSeek API（兼容 OpenAI SDK）
"""

import time

from openai import (
    OpenAI,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)
from .config import LLM_CONFIG

client = OpenAI(
    api_key=LLM_CONFIG["api_key"],
    base_url=LLM_CONFIG["base_url"],
)


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """
    调用 DeepSeek Chat API（带超时和重试）

    参数:
        messages: 对话历史，OpenAI 格式
        tools:    工具 schema 列表，None 表示不传工具

    返回:
        {
            "role": "assistant",
            "content": str | None,          # 文本回复（最终答案时）
            "tool_calls": list[dict] | None # 工具调用（需要执行时）
        }

    注意: DeepSeek 的 tool_calls 格式和 OpenAI 完全一致:
        tool_calls[0] = {
            "id": "call_xxx",
            "type": "function",
            "function": {"name": "query_db", "arguments": '{"sql":"..."}'}
        }
    """
    kwargs = {
        "model": LLM_CONFIG["model"],
        "messages": messages,
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
    }

    if tools:
        kwargs["tools"] = tools

    # ============================================================
    # 带重试的调用：只对临时性错误重试（超时/网络/5xx）
    # ============================================================
    max_retries = LLM_CONFIG.get("max_retries", 2)
    retry_delay = LLM_CONFIG.get("retry_delay", 2)
    timeout = LLM_CONFIG.get("timeout", 30)

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                **kwargs,
                timeout=timeout,
            )
            break   # 成功，跳出重试循环
        except (APITimeoutError, APIConnectionError, InternalServerError) as e:
            if attempt == max_retries:
                # 最后一次也失败，抛给上层
                raise
            # 递增退避：2s、4s...
            sleep_sec = retry_delay * (attempt + 1)
            print(f"⚠️ LLM 调用失败（{type(e).__name__}），{sleep_sec}s 后重试 "
                  f"({attempt + 1}/{max_retries})")
            time.sleep(sleep_sec)

    msg = response.choices[0].message

    # 构造统一返回格式
    result = {"role": "assistant", "content": msg.content}

    if msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    else:
        result["tool_calls"] = None

    return result
