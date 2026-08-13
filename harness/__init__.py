"""
Harness — Agent 运行时治理层

主类 Harness 组合四个子模块，通过四个钩子方法暴露给 agent.py：
  - auth        权限检查（before_tool 拦截）
  - guardrails  SQL 护栏 + 结果脱敏（before_tool 拦截 / after_tool 修改）
  - monitor     指标统计（全程累计）
  - audit       审计日志（写文件）

agent.py 只在关键节点调用钩子方法，不关心内部有多少子模块。
"""

import time

from .auth import Auth
from .guardrails import Guardrails
from .monitor import Monitor
from .audit import Audit


class Harness:
    def __init__(self, config: dict | None = None):
        config = config or {}

        # 组合四个子模块
        # 注意：不存 role！role 是请求级参数，随每次调用传入，
        # 这样才能支持多用户（每个用户角色不同）。
        self.auth = Auth(config.get("roles", {}))
        self.guardrails = Guardrails()
        self.monitor = Monitor()
        self.audit = Audit(
            log_file=config.get("audit", {}).get("log_file", "logs/audit.log")
        )

    # ============================================================
    # 挂点 1：请求开始
    # ============================================================
    def before_request(self, role: str, question: str) -> None:
        self.monitor.record_request()
        self.audit.log({"event": "request", "role": role, "question": question})

    # ============================================================
    # 挂点 2：工具执行前（可拦截）
    #   返回 None = 放行，dict = 拦截
    # ============================================================
    def before_tool(self, role: str, tool_name: str, args: dict):
        # ① 权限检查
        block = self.auth.check(role, tool_name)
        if block:
            self.monitor.record_block()
            self.audit.log({"event": "blocked", "reason": "auth",
                            "tool": tool_name, "role": role})
            return block

        # ② SQL 护栏检查
        if tool_name == "query_db":
            err = self.guardrails.check_sql(args.get("sql", ""))
            if err:
                self.monitor.record_block()
                self.audit.log({"event": "blocked", "reason": "sql",
                                "tool": tool_name, "detail": err})
                return {"error": err}

        # ③ 放行：记数 + 审计
        self.monitor.record_tool_call()
        self.audit.log({"event": "tool_call", "tool": tool_name, "args": args})
        return None

    # ============================================================
    # 挂点 3：工具执行后（可修改结果）
    # ============================================================
    def after_tool(self, tool_name: str, result_str: str) -> str:
        # 结果脱敏
        return self.guardrails.sanitize(result_str)

    # ============================================================
    # 挂点 4：请求结束
    # ============================================================
    def on_complete(self, answer: str) -> None:
        duration = self.monitor.finish()
        self.audit.log({"event": "complete", "duration_sec": round(duration, 2),
                        "answer_preview": answer[:100]})
