"""
权限检查模块
控制"角色"能调用"哪些工具"
"""


class Auth:
    def __init__(self, roles: dict):
        """
        roles 格式:
            {
                "admin":  {"tools": ["query_db", "get_schema", "get_table_info"]},
                "viewer": {"tools": ["get_schema", "get_table_info"]},
            }
        """
        self.roles = roles

    def check(self, role: str, tool_name: str):
        """
        检查某角色是否有权调用某工具。

        返回:
            None = 放行
            dict = 拦截（作为错误结果返回给 LLM）
        """
        allowed = self.roles.get(role, {}).get("tools", [])
        if tool_name not in allowed:
            return {"error": f"角色 {role} 无权调用工具 {tool_name}"}
        return None
