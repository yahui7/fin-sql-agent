"""
对话记忆模块
存储用户和 Agent 之间的 Q&A 历史，支持多轮追问
"""


class ConversationMemory:
    """带容量上限的对话历史管理器"""

    def __init__(self, max_turns=10):
        self.messages = []          # [{"role": "user", "content": ...}, ...]
        self.max_turns = max_turns  # 最多保留几轮

    def add_turn(self, user_msg: str, assistant_msg: str):
        """一轮对话结束后调用，存入 Q&A 对"""
        self.messages.append({"role": "user", "content": user_msg})
        self.messages.append({"role": "assistant", "content": assistant_msg})
        # 超出上限，丢掉最早的一轮
        limit = self.max_turns * 2
        if len(self.messages) > limit:
            self.messages = self.messages[-limit:]

    def get_history(self) -> list[dict]:
        """返回当前历史消息，用于注入 LLM 上下文"""
        return list(self.messages)

    def clear(self):
        """清空所有记忆"""
        self.messages = []

    def __len__(self):
        return len(self.messages) // 2  # 返回轮数
