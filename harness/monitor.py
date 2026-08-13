"""
指标统计模块
累计查询次数、工具调用次数、耗时、拦截次数，提供报告。
"""

import time


class Monitor:
    def __init__(self):
        self.total_queries = 0       # 请求总数
        self.total_tool_calls = 0    # 工具调用总数
        self.total_duration = 0.0    # 总耗时（秒）
        self.blocked_count = 0       # 被拦截次数
        self._start_time = None      # 当前请求开始时间

    def record_request(self):
        """请求开始（before_request 调用）"""
        self.total_queries += 1
        self._start_time = time.time()

    def record_tool_call(self):
        """工具调用 +1（before_tool 放行时调用）"""
        self.total_tool_calls += 1

    def record_block(self):
        """拦截 +1（before_tool 拦截时调用）"""
        self.blocked_count += 1

    def finish(self) -> float:
        """请求结束（on_complete 调用），返回本次耗时"""
        if self._start_time:
            duration = time.time() - self._start_time
            self.total_duration += duration
            self._start_time = None
            return duration
        return 0.0

    def report(self) -> dict:
        """返回统计报告"""
        avg = self.total_duration / self.total_queries if self.total_queries else 0.0
        return {
            "total_queries": self.total_queries,
            "total_tool_calls": self.total_tool_calls,
            "avg_duration_sec": round(avg, 2),
            "blocked_count": self.blocked_count,
        }
