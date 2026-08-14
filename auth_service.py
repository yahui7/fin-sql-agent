"""
登录认证服务（简单 token）

当前实现：
  - 用户列表从 config.USERS 读取
  - token 存内存字典，服务重启失效
  - 密码明文（学习阶段）

后续可升级：
  - 用户存数据库
  - 密码 bcrypt 哈希
  - token 存 Redis 或加过期时间
"""

import secrets
from config import USERS

# token -> 用户信息（内存存储，重启清空）
TOKEN_STORE = {}


def login(username: str, password: str) -> dict | None:
    """
    验证用户名密码。

    成功返回:
        {"token": "a1b2...", "role": "admin", "username": "admin"}
    失败返回:
        None
    """
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None

    token = secrets.token_hex(32)   # 64 位随机十六进制字符串
    TOKEN_STORE[token] = {"username": username, "role": user["role"]}
    return {"token": token, "role": user["role"], "username": username}


def get_user_from_token(token: str) -> dict | None:
    """从 token 解析用户，无效或不存在返回 None"""
    if not token:
        return None
    return TOKEN_STORE.get(token)


def logout(token: str) -> None:
    """删除 token，使其失效"""
    TOKEN_STORE.pop(token, None)
