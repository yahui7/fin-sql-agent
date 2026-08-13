# Text2SQL Agent — 代码版

> 用 DeepSeek + MySQL 搭建的金融数据查询 Agent，支持自然语言查询和数据质量检查。

## 架构

```
用户（命令行）
    ↓
main.py ─── 交互循环
    ↓
agent.py ─── ReAct 循环（思考 → 调工具 → 看结果 → 再思考）
    ↓
llm.py ─── DeepSeek API（OpenAI SDK 格式的 Function Calling）
    ↓
tools/database.py ─── MySQL 查询（本地直连，无需 ngrok）
    ↓
MySQL（financial 数据库，4 张金融表）
```

## 文件说明

| 文件 | 作用 | 你该看什么 |
|-----|------|----------|
| `agent.py` | **ReAct 循环核心** | 最重要！理解 Agent 怎么"想→做→看"循环 |
| `main.py` | 命令行入口 | 交互循环很简单 |
| `llm.py` | DeepSeek 封装 | Function Calling 怎么传参的 |
| `config.py` | 集中配置 | 改密码和 API Key |
| `tools/registry.py` | 工具注册 | Python 函数怎么变成 LLM 的 tool |
| `tools/database.py` | 数据库操作 | 3 个工具的具体实现 |
| `prompts/system.md` | 系统提示词 | Agent 的"大脑"，控制行为 |
| `prompts/few_shot.yaml` | 查询示例 | 帮助 Agent 理解 SQL 模式 |
| `scripts/import_data.py` | 数据导入 | CSV → MySQL |

## 启动步骤

### 1. 安装依赖

```bash
pip install openai mysql-connector-python
```

### 2. 创建数据库

```sql
CREATE DATABASE financial CHARACTER SET utf8mb4;
```

### 3. 导入金融数据

```bash
cd scripts
python import_data.py
```

### 4. 修改 config.py

- `LLM_CONFIG.api_key` → 你的 DeepSeek API Key
- `DB_CONFIG.password` → 你的 MySQL 密码
- `DB_CONFIG.database` → 你的库名

### 5. 开始查询

```bash
python main.py
```

## 测试问题

| 类型 | 问题 | 预期行为 |
|-----|------|---------|
| 基础 | 数据库有哪些表？ | get_schema → 列出 4 张表 |
| 业务 | 7 月交易金额最高的 5 笔 | get_table_info → SQL → 结果 |
| 质量 | 有多少客户没填证件有效期？ | get_table_info → IS NULL SQL |
| 质量 | 姓名包含 * 的客户 | LIKE '%*%' SQL |
| 关联 | 余额最高的 5 个账户属于谁？ | JOIN account + customer |
| 混合 | 没填有效期的客户有没有仍在交易的？ | 子查询或 JOIN + IS NULL |

## 批量测试

```bash
python tests/test_queries.py
```

## 学习路线

1. **先跑通**：改 config.py → 导数据 → `python main.py` → 问一个问题
2. **读 agent.py**：理解 ReAct 循环的 for 循环结构
3. **读 prompts/system.md**：理解提示词怎么控制 Agent 行为
4. **改工具**：在 `tools/database.py` 加一个新函数，在 `registry.py` 注册
5. **拆 Agent**：把 Agent 拆成 SchemaAgent + SQLAgent + ReviewAgent

## 和 Dify 版的对应关系

| Dify 版 | 代码版 | 说明 |
|--------|-------|------|
| Agent 节点 | `agent.py` | ReAct 循环 |
| Instructions 字段 | `prompts/system.md` | 系统提示词 |
| 自定义 API 工具 | `tools/database.py` | 工具函数 |
| 导入 OpenAPI JSON | `tools/registry.py` | 工具注册 |
| 日志面板 | 终端 print | 观察 ReAct 过程 |
| ngrok 隧道 | 不需要 | 本地直连 |
