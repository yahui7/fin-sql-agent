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

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import AGENT_CONFIG, HARNESS_CONFIG
from agent import run
from memory import ConversationMemory
from harness import Harness

app = FastAPI(title="金融数据查询 Agent")

# ============================================================
# Harness（治理层）：权限/护栏/脱敏/审计/监控
# ============================================================
# Harness 是无状态的，不绑定角色。role 在每次请求时传入。
harness = Harness(config=HARNESS_CONFIG)

# ============================================================
# 系统提示词（启动时加载一次）
# ============================================================
PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts", "system.md",
)
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


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


# ============================================================
# 路由
# ============================================================
@app.get("/", response_class=HTMLResponse)
def index():
    """返回聊天页面"""
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/chat")
def chat(req: ChatRequest):
    """处理一次查询：调 Agent，返回答案和 ReAct 步骤"""
    if not req.question.strip():
        return JSONResponse({"error": "问题不能为空"}, status_code=400)

    # ============================================================
    # 角色解析：当前写死 admin，将来接入登录后从 token 里取
    #   将来：role = get_current_user(token).role
    # ============================================================
    role = "admin"

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
    }


@app.post("/clear")
def clear(req: ChatRequest):
    """清空某会话的记忆"""
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
