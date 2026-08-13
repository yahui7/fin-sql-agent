"""
LLM 封装 — DeepSeek API（兼容 OpenAI SDK）
"""

from openai import OpenAI
from config import LLM_CONFIG

client = OpenAI(
    api_key=LLM_CONFIG["api_key"],
    base_url=LLM_CONFIG["base_url"],
)


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """
    调用 DeepSeek Chat API

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

    response = client.chat.completions.create(**kwargs)
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
