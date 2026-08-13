"""
工具注册中心
把 Python 函数注册为 LLM 可调用的 Function Calling Tool
"""

import json
from .database import query_db, get_schema, get_table_info

# ============================================================
# 函数名 → 函数对象 映射
# 新增工具只需：1) 在这里加一行映射  2) 在 TOOL_SCHEMAS 加一个 schema
# ============================================================
TOOLS_MAP = {
    "get_schema": get_schema,
    "get_table_info": get_table_info,
    "query_db": query_db,
}

# ============================================================
# Tool Schemas（DeepSeek / OpenAI Function Calling 格式）
# ============================================================
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": (
                "获取数据库中所有表的名称、每个表的列名和数据类型。"
                "当你不知道有哪些表、或者不确定某个表的字段名时，必须先调用此工具。"
                "不需要参数。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_info",
            "description": (
                "获取指定表的完整结构信息，包括："
                "1) 总行数；2) 所有列名；3) 前 3 行样本数据。"
                "在生成 SQL 查询之前，你必须调用此工具确认表的真实字段名和数据类型。"
                "不要猜测字段名！"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "要查询的表名，例如 customer、account、transactions",
                    }
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_db",
            "description": (
                "执行一条只读的 SELECT 查询语句，返回查询结果。"
                "只允许 SELECT，禁止 INSERT/UPDATE/DELETE/DROP 等修改操作。"
                "查询结果自动限制最多 100 行。"
                "表名和字段名必须使用数据库中实际存在的名称（先通过 get_schema/get_table_info 确认）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "合法的 SELECT 查询语句",
                    }
                },
                "required": ["sql"],
            },
        },
    },
]


def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    根据 tool_name 找到对应函数，执行并返回 JSON 字符串。

    参数:
        tool_name: 函数名，如 "query_db"
        tool_args: 函数参数，如 {"sql": "SELECT 1"}

    返回:
        工具执行结果的 JSON 字符串
    """
    func = TOOLS_MAP.get(tool_name)
    if not func:
        return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)

    try:
        result = func(**tool_args)
        # 对长结果做截断，避免超出 LLM 上下文
        from config import AGENT_CONFIG

        json_str = json.dumps(result, ensure_ascii=False, default=str)
        limit = AGENT_CONFIG.get("result_truncate", 2000)
        if len(json_str) > limit:
            json_str = json_str[:limit] + f"...(结果已截断，共 {len(result.get('rows', []))} 行)"
        return json_str
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
