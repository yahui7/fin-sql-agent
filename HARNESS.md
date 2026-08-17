# Harness（运行时治理层）

Harness 为 Agent 提供生产级的运行时治理能力，在查询执行流程的关键节点插入权限、安全、审计和监控逻辑。

## 解决的问题

- **权限控制** — 基于角色限制可调用的工具
- **安全护栏** — 只读强制 + 危险 SQL 拦截 + 敏感信息脱敏
- **审计日志** — 每次查询全程记录，合规可追溯
- **指标监控** — 查询数、工具调用数、耗时、拦截数统计

## 架构

```
请求 → run(question, role)
          │
          ├─ before_request(role, question)   → 指标计数 + 审计记录
          │
          ├─ before_tool(role, tool, args)    → 权限检查
          │                                    → SQL 护栏检查
          │                                    返回 None=放行 / dict=拦截
          │
          ├─ execute_tool(...)                → 实际执行
          │
          ├─ after_tool(tool, result)         → 敏感信息脱敏
          │
          └─ on_complete(answer)              → 指标统计 + 审计记录
```

## 目录结构

```
harness/
├── __init__.py      # Harness 主类，组合各模块，暴露 4 个钩子
├── auth.py          # 权限检查（角色 → 可用工具）
├── guardrails.py    # SQL 检查 + 身份证/手机号脱敏
├── monitor.py       # 指标统计
└── audit.py         # 审计日志（JSON Lines）
```

## 钩子与模块

| 钩子 | 触发时机 | 作用 |
|-----|---------|------|
| `before_request` | 请求开始 | 指标计数 + 审计记录 |
| `before_tool` | 工具执行前 | 权限检查 + SQL 护栏（可拦截） |
| `after_tool` | 工具执行后 | 敏感信息脱敏（可修改结果） |
| `on_complete` | 请求结束 | 耗时统计 + 完成记录 |

## 配置

在 `core/config.py` 中配置：

```python
HARNESS_CONFIG = {
    "roles": {
        "admin":  {"tools": ["query_db", "get_schema", "get_table_info"]},
        "viewer": {"tools": ["get_schema", "get_table_info"]},
    },
    "audit": {
        "log_file": "logs/audit.log",
    },
}
```

## 脱敏规则

| 类型 | 规则 | 示例 |
|-----|------|------|
| 身份证号 | 保留前 6 后 4 位 | `110101********1234` |
| 手机号 | 保留前 3 后 4 位 | `138****5678` |

## 使用

```python
from harness import Harness
from core.config import HARNESS_CONFIG

harness = Harness(config=HARNESS_CONFIG)

answer = run(
    question="查张三账户",
    system_prompt=system_prompt,
    harness=harness,
    role="admin",   # 从登录信息中解析
)
```

## 扩展新治理规则

在对应子模块中添加逻辑即可，`agent.py` 无需改动：

- **新增权限角色** — 修改 `HARNESS_CONFIG["roles"]`
- **新增脱敏字段** — 修改 `guardrails.py` 中的正则模式
- **新增 SQL 拦截** — 修改 `guardrails.py` 中的 `DANGEROUS_KEYWORDS`
- **新增指标** — 修改 `monitor.py`

## 设计原则

1. **钩子是骨架** — `agent.py` 只留挂点，不关心治理逻辑
2. **主类只编排** — Harness 主类负责"什么时候调谁"，子模块负责"具体怎么做"
3. **before 负责拦，after 负责改**
4. **无状态** — role 是请求级参数，不在 Harness 实例上存储，支持多用户
5. **纵深防御** — SQL 检查在 `tools/database.py` 和 `guardrails.py` 各有一道
6. **向后兼容** — `harness=None` 时行为完全不变
