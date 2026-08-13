"""
数据库工具函数
提供三个核心能力：查表结构、看表详情、执行 SQL
"""

import mysql.connector
from config import DB_CONFIG


def get_conn():
    """获取 MySQL 数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# 工具 1：获取所有表结构
# ============================================================
def get_schema() -> dict:
    """
    返回数据库中所有表的名称、列名、数据类型、是否可空。
    这是 Agent 的第一个调用的工具——了解有哪些表可用。
    """
    sql = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, (DB_CONFIG["database"],))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    tables = {}
    for row in rows:
        table = row["TABLE_NAME"]
        if table not in tables:
            tables[table] = []
        tables[table].append(
            {
                "column": row["COLUMN_NAME"],
                "type": row["DATA_TYPE"],
                "nullable": row["IS_NULLABLE"] == "YES",
                "comment": row.get("COLUMN_COMMENT", "") or "",
            }
        )

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
    if not table_name:
        return {"error": "参数 table_name 不能为空"}

    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        # 总行数
        cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table_name}`")
        count = cur.fetchone()["cnt"]

        # 前 3 行样本
        cur.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
        rows = cur.fetchall()
        columns = list(rows[0].keys()) if rows else []

        cur.close()
        conn.close()

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

    # === 执行查询 ===
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        rows = cur.fetchall()
        columns = list(rows[0].keys()) if rows else []
        cur.close()
        conn.close()

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except Exception as e:
        return {"error": f"SQL 执行失败: {str(e)}", "sql": sql}
