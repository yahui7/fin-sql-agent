"""
CSV 数据导入 MySQL 脚本

用法:
    python import_data.py

前提:
    1. MySQL 已运行，数据库 financial（或 config.py 中指定的库）已创建
    2. 已安装依赖: pip install pandas mysql-connector-python
    3. data/ 目录下有 customer.csv, account.csv, transactions.csv, product.csv
"""

import os
import sys
import csv
import mysql.connector

# 把项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# 表名 → CSV 文件名映射
TABLES = {
    "customer":     "customer.csv",
    "product":      "product.csv",
    "account":      "account.csv",
    "transactions": "transactions.csv",
}


def create_tables(conn):
    """根据 CSV 字段建表"""
    cur = conn.cursor()

    # 删旧表（注意顺序：先删有外键的）
    cur.execute("DROP TABLE IF EXISTS transactions")
    cur.execute("DROP TABLE IF EXISTS account")
    cur.execute("DROP TABLE IF EXISTS product")
    cur.execute("DROP TABLE IF EXISTS customer")

    cur.execute("""
        CREATE TABLE customer (
            customer_id VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100),
            id_type VARCHAR(20),
            id_number VARCHAR(50),
            id_expiry_date DATE,
            nationality VARCHAR(50),
            birth_date DATE,
            occupation VARCHAR(100),
            risk_level VARCHAR(10),
            phone VARCHAR(20),
            email VARCHAR(100),
            address VARCHAR(500)
        ) CHARACTER SET utf8mb4
    """)

    cur.execute("""
        CREATE TABLE product (
            product_id VARCHAR(20) PRIMARY KEY,
            product_name VARCHAR(200),
            product_type VARCHAR(50),
            risk_level VARCHAR(10),
            issuer VARCHAR(100),
            status VARCHAR(20),
            launch_date DATE,
            maturity_date DATE
        ) CHARACTER SET utf8mb4
    """)

    cur.execute("""
        CREATE TABLE account (
            account_id VARCHAR(20) PRIMARY KEY,
            customer_id VARCHAR(20),
            product_id VARCHAR(20),
            account_type VARCHAR(20),
            status VARCHAR(20),
            balance DECIMAL(18,2),
            currency VARCHAR(10),
            open_date DATE,
            close_date DATE,
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        ) CHARACTER SET utf8mb4
    """)

    cur.execute("""
        CREATE TABLE transactions (
            transaction_id VARCHAR(20) PRIMARY KEY,
            account_id VARCHAR(20),
            customer_id VARCHAR(20),
            transaction_type VARCHAR(20),
            amount DECIMAL(18,2),
            currency VARCHAR(10),
            counterparty_info VARCHAR(500),
            transaction_date DATETIME,
            channel VARCHAR(50),
            purpose VARCHAR(100),
            FOREIGN KEY (account_id) REFERENCES account(account_id),
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ) CHARACTER SET utf8mb4
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

        columns = rows[0].keys()
        placeholders = ", ".join(["%s"] * len(columns))
        cols_str = ", ".join([f"`{c}`" for c in columns])

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

    # 连接数据库
    db_name = DB_CONFIG.get("database", "financial")
    print(f"📌 目标数据库: {db_name}")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print(f"✅ MySQL 连接成功\n")
    except mysql.connector.Error as e:
        print(f"❌ MySQL 连接失败: {e}")
        print("   请检查 config.py 中的 DB_CONFIG")
        sys.exit(1)

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
