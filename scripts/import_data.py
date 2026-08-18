"""
CSV 数据导入 SQLite 脚本

用法:
    python import_data.py

前提:
    1. 已安装依赖: pip install -r requirements.txt
    2. data/ 目录下有 customer.csv, account.csv, transactions.csv, product.csv

产出:
    data/financial.db（SQLite 数据库文件）
"""

import os
import sys
import csv
import sqlite3

# 把项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import DB_CONFIG

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# 表名 → CSV 文件名映射（顺序重要：先建被引用表）
TABLES = {
    "customer":     "customer.csv",
    "product":      "product.csv",
    "account":      "account.csv",
    "transactions": "transactions.csv",
}


def create_tables(conn):
    """根据 CSV 字段建表"""
    cur = conn.cursor()

    # 删旧表（注意顺序：先删有外键的表）
    cur.execute("DROP TABLE IF EXISTS transactions")
    cur.execute("DROP TABLE IF EXISTS account")
    cur.execute("DROP TABLE IF EXISTS product")
    cur.execute("DROP TABLE IF EXISTS customer")

    cur.execute("""
        CREATE TABLE customer (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            id_type TEXT,
            id_number TEXT,
            id_expiry_date TEXT,
            nationality TEXT,
            birth_date TEXT,
            occupation TEXT,
            risk_level TEXT,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE product (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            product_type TEXT,
            risk_level TEXT,
            issuer TEXT,
            status TEXT,
            launch_date TEXT,
            maturity_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE account (
            account_id TEXT PRIMARY KEY,
            customer_id TEXT,
            product_id TEXT,
            account_type TEXT,
            status TEXT,
            balance REAL,
            currency TEXT,
            open_date TEXT,
            close_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT,
            customer_id TEXT,
            transaction_type TEXT,
            amount REAL,
            currency TEXT,
            counterparty_info TEXT,
            transaction_date TEXT,
            channel TEXT,
            purpose TEXT
        )
    """)

    conn.commit()
    cur.close()
    print("✅ 4 张表创建完成")


def import_csv(conn, table_name, csv_path):
    """将 CSV 文件导入指定表"""
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print(f"  ⚠️ {table_name}: CSV 文件为空")
            return 0

        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        cols_str = ", ".join([f'"{c}"' for c in columns])

        sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"

        cur = conn.cursor()
        count = 0
        for row in rows:
            values = [
                None if v == "" or v == "NULL" or v == "\\N" else v
                for v in row.values()
            ]
            try:
                cur.execute(sql, values)
                count += 1
            except Exception as e:
                print(f"  ❌ 导入失败，行 {count+1}: {e}")
                conn.rollback()
                cur.close()
                return count

        conn.commit()
        cur.close()
        return count


def main():
    # 检查 data 目录
    if not os.path.isdir(DATA_DIR):
        print(f"❌ data 目录不存在: {DATA_DIR}")
        sys.exit(1)

    db_path = DB_CONFIG["path"]
    print(f"📌 目标数据库: {db_path}")

    # 确保 data 目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 连接 SQLite
    conn = sqlite3.connect(db_path)
    print("✅ SQLite 连接成功\n")

    # 建表
    print("📦 创建表结构...")
    create_tables(conn)

    # 导入数据
    print("\n📥 导入数据...")
    for table_name, csv_file in TABLES.items():
        csv_path = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(csv_path):
            print(f"  ⚠️ {csv_file} 不存在，跳过 {table_name}")
            continue
        count = import_csv(conn, table_name, csv_path)
        print(f"  ✅ {table_name}: 导入 {count} 行")

    conn.close()
    print("\n🎉 导入完成！可以运行 main.py 开始查询。")


if __name__ == "__main__":
    main()
