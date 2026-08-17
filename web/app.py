"""
Text2SQL Agent — Web 服务（FastAPI）

启动:
    uvicorn web.app:app --host 0.0.0.0 --port 8765

浏览器打开 http://localhost:8765 即可使用。
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

# 确保能导入项目根目录的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from core.config import AGENT_CONFIG, HARNESS_CONFIG
from core.agent import run
from core.memory import ConversationMemory
from harness import Harness
from core.auth_service import login, get_user_from_token, logout

app = FastAPI(title="金融数据查询 Agent")

# ============================================================
# Harness（治理层）：权限/护栏/脱敏/审计/监控
# ============================================================
# Harness 是无状态的，不绑定角色。role 在每次请求时传入。
harness = Harness(config=HARNESS_CONFIG)

# ============================================================
# 系统提示词（启动时加载一次，动态注入数据库结构说明）
# ============================================================
PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts", "system.md",
)
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    _template = f.read()

from core.schema_docs import build_schema_doc
SYSTEM_PROMPT = _template.replace("{{TABLE_SCHEMA}}", build_schema_doc())


# ============================================================
# 会话管理：每个浏览器窗口一个独立 memory
# ============================================================
sessions = {}          # session_id -> {"memory": ConversationMemory, "last_active": datetime}
SESSION_TIMEOUT = timedelta(minutes=30)   # 30 分钟不活动则清理


def get_memory(session_id: str) -> ConversationMemory:
    """获取或创建某个会话的记忆"""
    now = datetime.now()

    # 顺便清理过期会话
    expired = [sid for sid, s in sessions.items()
               if now - s["last_active"] > SESSION_TIMEOUT]
    for sid in expired:
        del sessions[sid]

    if session_id not in sessions:
        sessions[session_id] = {
            "memory": ConversationMemory(
                max_turns=AGENT_CONFIG.get("memory_max_turns", 10)
            ),
            "last_active": now,
        }
    else:
        sessions[session_id]["last_active"] = now

    return sessions[session_id]["memory"]


# ============================================================
# 请求模型
# ============================================================
class ChatRequest(BaseModel):
    session_id: str
    question: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ============================================================
# 路由
# ============================================================
@app.get("/", response_class=HTMLResponse)
def index():
    """返回聊天页面"""
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/login")
def login_endpoint(req: LoginRequest):
    """登录：验证用户名密码，返回 token"""
    result = login(req.username, req.password)
    if not result:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    return result


@app.post("/logout")
def logout_endpoint(authorization: str = Header(None)):
    """退出登录：使 token 失效"""
    token = _extract_token(authorization)
    logout(token)
    return {"ok": True}


def _extract_token(authorization: str | None) -> str:
    """从 Authorization header 提取 token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return ""


@app.post("/chat")
def chat(req: ChatRequest, authorization: str = Header(None)):
    """处理一次查询：调 Agent，返回答案和 ReAct 步骤"""
    if not req.question.strip():
        return JSONResponse({"error": "问题不能为空"}, status_code=400)

    # ============================================================
    # 认证：从 token 解析用户，拿到真实角色
    # ============================================================
    token = _extract_token(authorization)
    user = get_user_from_token(token)
    if not user:
        return JSONResponse({"error": "未登录或登录已过期"}, status_code=401)

    role = user["role"]
    username = user["username"]

    memory = get_memory(req.session_id)

    # 收集 ReAct 步骤
    steps = []

    def on_step(event):
        steps.append(event)

    # 调 Agent
    answer = run(
        user_question=req.question,
        system_prompt=SYSTEM_PROMPT,
        memory=memory,
        callback=on_step,
        harness=harness,
        role=role,
    )

    # 存入记忆
    memory.add_turn(req.question, answer)

    return {
        "answer": answer,
        "steps": steps,
        "role": role,
        "username": username,
    }


@app.post("/clear")
def clear(req: ChatRequest, authorization: str = Header(None)):
    """清空某会话的记忆"""
    token = _extract_token(authorization)
    if not get_user_from_token(token):
        return JSONResponse({"error": "未登录"}, status_code=401)

    if req.session_id in sessions:
        sessions[req.session_id]["memory"].clear()
    return {"ok": True}


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok", "sessions": len(sessions)}


@app.get("/stats")
def stats():
    """查看指标统计"""
    return harness.monitor.report()
