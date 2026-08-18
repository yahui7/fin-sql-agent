"""
数据库工具函数（SQLite 版）
提供三个核心能力：查表结构、看表详情、执行 SQL

安全设计：
  1. 表名白名单（层次B）：只允许查询数据库中真实存在的表
  2. 连接管理：使用 get_cursor() 上下文管理器，保证连接一定关闭
"""

import re
import sqlite3
from contextlib import contextmanager

from core.config import DB_CONFIG


def _dict_factory(cursor, row):
    """让 fetchall 返回 dict 列表（等价于 MySQL 的 dictionary=True）"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _regexp(pattern, value):
    """注册给 SQLite 的 REGEXP 函数（SQLite 默认不支持）"""
    if value is None:
        return False
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


def get_conn():
    """获取 SQLite 连接"""
    conn = sqlite3.connect(DB_CONFIG["path"])
    conn.row_factory = _dict_factory
    conn.create_function("REGEXP", 2, _regexp)   # 注册 REGEXP
    return conn


@contextmanager
def get_cursor():
    """
    上下文管理器：获取游标，用完自动关闭游标和连接。

    用法:
        with get_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    无论中间是否抛异常，连接都会被关闭，避免连接泄漏。
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()
        conn.close()


# ============================================================
# 表名白名单
# ============================================================
def _get_valid_tables() -> set:
    """查询数据库中真实存在的所有表名"""
    with get_cursor() as cur:
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return {row["name"] for row in cur.fetchall()}


def _validate_table_name(table_name: str) -> str | None:
    """
    校验表名是否合法（层次B：必须在真实表列表里）。

    返回:
        None = 合法
        str  = 错误信息
    """
    if not table_name:
        return "表名不能为空"

    if table_name not in _get_valid_tables():
        return f"表 {table_name} 不存在"

    return None


# ============================================================
# 工具 1：获取所有表结构
# ============================================================
def get_schema() -> dict:
    """
    返回数据库中所有表的名称、列名、数据类型、是否可空。
    这是 Agent 的第一个调用的工具——了解有哪些表可用。
    """
    tables = {}
    for table_name in sorted(_get_valid_tables()):
        with get_cursor() as cur:
            cur.execute(f'PRAGMA table_info("{table_name}")')
            cols = cur.fetchall()

        # PRAGMA table_info 返回: cid, name, type, notnull, dflt_value, pk
        tables[table_name] = [
            {
                "column": c["name"],
                "type": c["type"],
                "nullable": c["notnull"] == 0,
                "comment": "",   # SQLite 无注释，含义由 schema_docs.py 提供
            }
            for c in cols
        ]

    return {"tables": tables, "table_count": len(tables)}


# ============================================================
# 工具 2：获取单表详细信息
# ============================================================
def get_table_info(table_name: str) -> dict:
    """
    获取指定表的：
    - 总行数
    - 所有列名
    - 前 3 行样本数据
    这是 Agent 生成 SQL 前必须调用的工具——确认字段名。
    """
    # 表名白名单校验
    err = _validate_table_name(table_name)
    if err:
        return {"error": err}

    try:
        with get_cursor() as cur:
            # 总行数
            cur.execute(f'SELECT COUNT(*) AS cnt FROM "{table_name}"')
            count = cur.fetchone()["cnt"]

            # 前 3 行样本
            cur.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
            rows = cur.fetchall()
            columns = list(rows[0].keys()) if rows else []

        return {
            "table": table_name,
            "total_rows": count,
            "columns": columns,
            "sample_rows": rows,
        }
    except Exception as e:
        return {"error": f"查询表 {table_name} 失败: {str(e)}"}


# ============================================================
# 工具 3：执行 SQL 查询
# ============================================================
def query_db(sql: str) -> dict:
    """
    执行只读 SELECT 查询，返回列名、行数据、行数。
    内置安全校验：只允许 SELECT、禁止危险关键字、自动加 LIMIT。
    """
    if not sql:
        return {"error": "参数 sql 不能为空"}

    sql = sql.strip()

    # === 安全检查 1：只允许 SELECT ===
    if not sql.upper().startswith("SELECT"):
        return {
            "error": "只允许 SELECT 查询",
            "detail": f"你的语句以 '{sql[:20]}...' 开头，已被拦截。请使用 SELECT。",
        }

    # === 安全检查 2：禁止危险关键字 ===
    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
                 "TRUNCATE", "CREATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"]
    upper_sql = sql.upper()
    for word in dangerous:
        if word in upper_sql:
            return {
                "error": f"禁止使用 {word}",
                "detail": f"检测到危险关键字 {word}，查询已被拦截。",
            }

    # === 自动加行数限制 ===
    if "LIMIT" not in upper_sql:
        sql = sql.rstrip(";") + " LIMIT 100"

    # === SQLite 兼容：反引号 → 双引号 ===
    sql = sql.replace("`", '"')

    # === 执行查询 ===
    try:
        with get_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = list(rows[0].keys()) if rows else []

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except Exception as e:
        return {"error": f"SQL 执行失败: {str(e)}", "sql": sql}
