"""
字段元数据 — 含义注释维护

原则：
  - 字段名、类型 → 从 MySQL 动态查询（get_schema），不在这里手写
  - 字段中文含义 → MySQL 建表时没有 COMMENT，在这里单独维护

这里只写"含义"，不写字段名和类型，避免和数据库重复。
"""

from tools.database import get_schema


# ============================================================
# 字段含义注释（MySQL 查不到的部分）
# ============================================================
FIELD_COMMENTS = {
    "customer": {
        "customer_id": "客户编号（主键）",
        "name": "客户姓名",
        "id_type": "证件类型（身份证/护照）",
        "id_number": "证件号码",
        "id_expiry_date": "证件有效期截止日",
        "nationality": "国籍",
        "birth_date": "出生日期",
        "occupation": "职业",
        "risk_level": "风险等级（高/中/低）",
        "phone": "手机号",
        "email": "邮箱",
        "address": "通讯地址",
    },
    "account": {
        "account_id": "账户编号（主键）",
        "customer_id": "客户编号（外键→customer）",
        "product_id": "产品编号（外键→product）",
        "account_type": "账户类型（活期/定期/理财）",
        "status": "状态（正常/冻结/关户）",
        "balance": "账户余额",
        "currency": "币种（CNY/USD/HKD）",
        "open_date": "开户日期",
        "close_date": "关户日期（正常账户为空）",
    },
    "transactions": {
        "transaction_id": "交易编号（主键）",
        "account_id": "账户编号（外键→account）",
        "customer_id": "客户编号（外键→customer）",
        "transaction_type": "交易类型（转账/缴费/消费/取现/存款）",
        "amount": "交易金额",
        "currency": "币种",
        "counterparty_info": "交易对手信息",
        "transaction_date": "交易时间",
        "channel": "渠道（手机银行/柜面/网银/ATM）",
        "purpose": "用途（投资理财/日常消费/投资收益/工资收入等）",
    },
    "product": {
        "product_id": "产品编号（主键）",
        "product_name": "产品名称",
        "product_type": "产品类型（公募-混合型/私募-股票多头/公募-债券型/理财）",
        "risk_level": "风险等级（高/中/低）",
        "issuer": "发行机构",
        "status": "状态（存续/到期/终止）",
        "launch_date": "发行日期",
        "maturity_date": "到期日期",
    },
}


# ============================================================
# 动态生成数据库结构说明
# ============================================================
def build_schema_doc() -> str:
    """
    从 MySQL 真实表结构 + FIELD_COMMENTS 生成 Markdown 表格。

    返回格式:
        # 数据库结构

        数据库包含 N 张表...

        ## customer（客户信息表）

        | 字段 | 类型 | 说明 |
        |-----|------|------|
        | customer_id | varchar | 客户编号（主键） |
        ...
    """
    schema = get_schema()
    tables = schema.get("tables", {})

    lines = ["# 数据库结构", "", f"数据库包含 {len(tables)} 张表。", ""]

    for table_name, columns in tables.items():
        lines.append(f"## {table_name}")
        lines.append("")
        lines.append("| 字段 | 类型 | 说明 |")
        lines.append("|-----|------|------|")
        for col in columns:
            col_name = col["column"]
            col_type = col["type"]
            comment = FIELD_COMMENTS.get(table_name, {}).get(col_name, "")
            lines.append(f"| {col_name} | {col_type} | {comment} |")
        lines.append("")

    return "\n".join(lines)
