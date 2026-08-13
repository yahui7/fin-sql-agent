"""
安全护栏模块
两个职责：
  1. SQL 安全检查（挂在 before_tool，可拦截）
  2. 结果脱敏（挂在 after_tool，可修改结果）

脱敏规则：
  身份证号 18 位 → 保留前 6 后 4，中间 8 位打码：110101********1234
  手机号 11 位   → 保留前 3 后 4，中间 4 位打码：138****5678
"""

import re


class Guardrails:
    # 危险 SQL 关键字
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT",
        "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    ]

    # 身份证号：18 位，前 6 后 4 保留
    ID_CARD_PATTERN = re.compile(r'(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)')
    # 手机号：1 开头 11 位，前 3 后 4 保留
    PHONE_PATTERN = re.compile(r'(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)')

    def check_sql(self, sql: str):
        """
        SQL 安全检查（独立于 database.py 的二次防线）。

        返回:
            None = 通过
            str  = 拦截原因
        """
        if not sql:
            return "SQL 不能为空"

        upper = sql.upper()
        for word in self.DANGEROUS_KEYWORDS:
            if word in upper:
                return f"禁止使用 {word}"
        return None

    def sanitize(self, result_str: str) -> str:
        """
        对结果字符串脱敏（身份证号、手机号打码）。

        返回脱敏后的字符串。
        """
        if not result_str:
            return result_str

        # 身份证号打码
        result_str = self.ID_CARD_PATTERN.sub(r'\1********\2', result_str)
        # 手机号打码
        result_str = self.PHONE_PATTERN.sub(r'\1****\2', result_str)
        return result_str
