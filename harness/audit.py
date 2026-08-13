"""
审计日志模块
记录每次查询的关键事件，追加写入 JSON Lines 文件。
每行一个 JSON 对象，便于后续分析。
"""

import os
import json
from datetime import datetime


class Audit:
    def __init__(self, log_file: str = "logs/audit.log"):
        self.log_file = log_file
        # 确保目录存在
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log(self, event: dict):
        """追加写一条审计记录"""
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **event,
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AUDIT] 写入日志失败: {e}")
