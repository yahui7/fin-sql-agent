# Harness 设计与改动记录

> 本文记录 Text2SQL Agent 项目中 Harness（运行时治理层）的设计与实现过程。

---

## 一、Harness 解决什么问题

没有 Harness 时，Agent 是"裸奔"的：

- ❌ 谁查的？不知道
- ❌ 查了什么 SQL？没记录
- ❌ 查了多久、花了多少 token？没统计
- ❌ 有没有人查不该查的表？拦不住
- ❌ 身份证号直接返回了？没脱敏

有 Harness 之后：

- ✅ 每次查询都有审计日志
- ✅ 权限控制谁能查什么
- ✅ SQL 二次安全检查
- ✅ 敏感字段自动脱敏
- ✅ 查询量/耗时/拦截数有统计

---

## 二、文件结构

```
harness/
├── __init__.py      # Harness 主类，组合四模块，暴露 4 个钩子
├── auth.py          # 权限检查（角色 → 可用工具）
├── guardrails.py    # SQL 检查 + 身份证/手机号脱敏
├── monitor.py       # 指标统计（查询数/工具数/耗时/拦截数）
└── audit.py         # 审计日志写文件（JSON Lines）
```

---

## 三、核心架构

```
请求 → run(question, role=xxx)
          │
          ├─ before_request(role, question)   → monitor 计数 + audit 记录
          │
          ├─ before_tool(role, tool, args)    → auth 权限检查
          │                                    → guardrails SQL 检查
          │                                    返回 None=放行 / dict=拦截
          │
          ├─ execute_tool(...)                 → 真正执行
          │
          ├─ after_tool(tool, result)          → guardrails 脱敏
          │
          └─ on_complete(answer)               → monitor 耗时 + audit 完成记录
```

---

## 四、钩子与子模块对应关系

| 钩子 | 挂点位置 | 触发的子模块 |
|-----|---------|------------|
| `before_request` | 请求开始 | monitor.record_request + audit.log |
| `before_tool` | 工具执行前 | auth.check + guardrails.check_sql + monitor |
| `after_tool` | 工具执行后 | guardrails.sanitize |
| `on_complete` | 请求结束 | monitor.finish + audit.log |

---

## 五、三个演进阶段

### 阶段 1：搭钩子（理解钩子机制）

在 `agent.py` 的 `run()` 里插入 4 个挂点，用一个简单的 `AuditHarness`（只打印日志）先跑通，验证钩子触发时机。

### 阶段 2：模块化（拆分治理职责）

把单一类拆成 4 个子模块 + 主类组合。主类只负责"编排"，子模块负责"具体逻辑"。

### 阶段 3：无状态化（为多用户做准备）

发现 role 存错位置（存进 Harness 实例），改为请求级参数：

```
改前：role 存在 Harness.self.role 里（全局定死）
改后：role 随每次调用传入（支持多用户不同角色）
```

---

## 六、配置项（config.py 的 HARNESS_CONFIG）

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

---

## 七、验证方式

| 功能 | 验证 |
|-----|------|
| 脱敏 | 查客户信息，身份证号 `110101********1234`、手机号 `138****5678` |
| 权限 | 改 role="viewer"，查数据被拦截 |
| 审计 | `cat logs/audit.log` 看 JSON 记录 |
| 监控 | 命令行 `stats` 命令，或网页访问 `/stats` |

---

## 八、关键设计原则

1. **钩子是骨架**：agent.py 只留挂点，不关心治理逻辑
2. **主类只编排**：Harness 主类负责"什么时候调谁"，子模块负责"具体怎么做"
3. **before 负责拦，after 负责改**
4. **无状态**：role 是请求级参数，不是 Harness 属性
5. **纵深防御**：SQL 检查在 database.py 和 guardrails.py 各有一道
6. **向后兼容**：`harness=None` 时行为完全不变

---

## 九、将来接入登录验证

当前 role 在 `web/app.py` 的 `/chat` 里写死：

```python
role = "admin"   # 当前写死
```

将来接入登录后只需改这一处：

```python
role = get_current_user(token).role   # 从登录信息取
```

Harness 和 agent.py 都不需要再动。
