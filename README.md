# fin-sql-agent

基于 DeepSeek + MySQL 的金融数据自然语言查询 Agent。用自然语言提问，得到解析后的查询结果，内置生产级的治理能力。

## 功能特性

- **ReAct 循环** — LLM 自主规划每一步：查看表结构 → 确认字段 → 生成 SQL → 执行 → 解读结果
- **多轮对话记忆** — 记住上下文，支持追问
- **Web 界面**（FastAPI）— 浏览器交互式聊天
- **Harness 治理层**
  - 基于角色的权限控制（`admin` / `viewer`）
  - SQL 护栏（只读强制、危险关键字拦截）
  - 敏感信息脱敏（身份证号、手机号）
  - 审计日志（JSON Lines）
  - 指标监控
- **命令行入口**，支持统计报告

## 架构

```
用户（命令行 或 浏览器）
    ↓
main.py / web/app.py ─── 入口
    ↓
agent.py ─── ReAct 循环（思考 → 调工具 → 观察 → 重复）
    ↓
llm.py ─── DeepSeek API（OpenAI 兼容的 Function Calling）
    ↓
tools/database.py ─── MySQL 查询（本地直连）
    ↓
MySQL（financial 数据库，4 张表）
```

```
请求 → run(question, role)
            ├─ before_request(role, question)   → 指标 + 审计
            ├─ before_tool(role, tool, args)    → 权限 + SQL 护栏
            ├─ execute_tool(...)                → 实际执行
            ├─ after_tool(tool, result)         → 敏感信息脱敏
            └─ on_complete(answer)              → 指标 + 审计
```

## 项目结构

| 文件 / 目录 | 用途 |
|------------|------|
| `agent.py` | ReAct 循环核心 |
| `main.py` | 命令行入口 |
| `llm.py` | DeepSeek API 封装（Function Calling） |
| `memory.py` | 多轮对话记忆 |
| `config.py` | 集中配置 |
| `tools/` | 数据库工具 + 工具注册 |
| `harness/` | 治理层（权限、护栏、审计、监控） |
| `web/` | FastAPI Web 服务 + 聊天界面 |
| `prompts/` | 系统提示词 + few-shot 示例 |
| `scripts/import_data.py` | CSV → MySQL 导入 |
| `tests/` | 测试套件 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的凭据：

```bash
DEEPSEEK_API_KEY=你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
MYSQL_PASSWORD=你的MySQL密码
MYSQL_DATABASE=financial
```

> **切勿提交 `.env`** — 它包含密钥，已被 gitignore 忽略。

### 3. 创建数据库

```sql
CREATE DATABASE financial CHARACTER SET utf8mb4;
```

### 4. 导入示例数据

```bash
cd scripts
python import_data.py
```

### 5. 运行

```bash
# 命令行模式
python main.py

# Web 模式
uvicorn web.app:app --host 0.0.0.0 --port 8765
# 然后打开 http://localhost:8765
```

## 示例查询

| 类型 | 问题 | 预期行为 |
|------|------|---------|
| 基础 | 数据库有哪些表？ | get_schema → 列出表 |
| 业务 | 7 月交易金额最高的 5 笔？ | schema → table_info → SQL → 结果 |
| 数据质量 | 有多少客户没填证件有效期？ | table_info → IS NULL SQL |
| 数据质量 | 姓名里含 `*` 的客户？ | LIKE '%*%' SQL |
| 关联 | 余额最高的 5 个账户属于谁？ | JOIN account + customer |
| 混合 | 没填有效期的客户还有交易吗？ | 子查询 / JOIN + IS NULL |

## 测试

```bash
python tests/test_queries.py
```

## 配置说明

| 配置项 | 说明 |
|--------|------|
| `LLM_CONFIG` | 模型、API Key、base URL、温度 |
| `DB_CONFIG` | MySQL 连接 |
| `AGENT_CONFIG` | 最大迭代次数、记忆轮数、详细模式 |
| `HARNESS_CONFIG` | 角色、审计日志路径 |

## 技术栈

Python · FastAPI · DeepSeek API · MySQL
