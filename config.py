"""
Text2SQL Agent — 集中配置
修改 .env 文件即可，不要在这里写明文密码
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================================
# DeepSeek API 配置
# ============================================================
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    "temperature": 0.1,
    "max_tokens": 4096,
}

# ============================================================
# MySQL 数据库配置
# ============================================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE", "financial"),
    "charset": "utf8mb4",
}

# ============================================================
# Agent 配置
# ============================================================
AGENT_CONFIG = {
    "max_iterations": 6,
    "verbose": True,
    "result_truncate": 2000,
    "memory_max_turns": 10,              # 对话记忆保留轮数
}

# ============================================================
# Harness 配置（治理层）
# ============================================================
HARNESS_CONFIG = {
    "roles": {
        "admin":  {"tools": ["query_db", "get_schema", "get_table_info"]},
        "viewer": {"tools": ["get_schema", "get_table_info"]},
    },
    "audit": {
        "log_file": "logs/audit.log",
    },
}

# ============================================================
# 用户列表（学习阶段用配置，后续换数据库）
# ============================================================
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "view":  {"password": "view123",  "role": "viewer"},
}
