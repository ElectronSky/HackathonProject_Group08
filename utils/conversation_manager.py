import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from .path_tools import get_abs_path

class ConversationManager:
    """
    对话历史管理器
    负责自然语言记账区域的对话历史记录的增删改查和持久化存储
    """

    def __init__(self, user_id: str, conversation_type: str = "accounting"):
        """
        初始化对话管理器

        Args:
            user_id: 用户唯一标识符
            conversation_type: 对话类型，用于区分记账页和财商助手页
        """
        self.user_id = user_id
        self.conversation_type = conversation_type
        # 在 data/conversations 下继续按场景分目录，避免记账页和财商页串历史
        self.conversation_dir = get_abs_path(f"data/conversations/{conversation_type}")
        self.conversation_file = os.path.join(self.conversation_dir, f"{user_id}_conversations.json")
        self._ensure_conversation_dir_exists()
        self._ensure_conversation_file_exists()

    def _ensure_conversation_dir_exists(self):
        """确保对话历史目录存在，不存在则创建"""
        if not os.path.exists(self.conversation_dir):
            os.makedirs(self.conversation_dir)

    def _ensure_conversation_file_exists(self):
        """确保用户对话文件存在，不存在则创建初始结构"""
        if not os.path.exists(self.conversation_file):
            initial_data = {
                "user_id": self.user_id,
                "conversation_type": self.conversation_type,
                "conversations": []
            }
            self._write_data(initial_data)

    def _read_data(self) -> dict:
        """读取用户对话历史数据"""
        with open(self.conversation_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_data(self, data: dict):
        """写入用户对话历史数据"""
        with open(self.conversation_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_new_conversation(self) -> Dict:
        """
        创建新对话

        Returns:
            dict: 新创建的对话对象
        """
        conversation_id = f"{self.conversation_type}_conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        new_conversation = {
            "id": conversation_id,
            "title": "新对话",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        data = self._read_data()
        data["conversations"].insert(0, new_conversation)  # 插入到最前面
        self._write_data(data)
        
        return new_conversation

    def create_new_conversation_with_title(self, title: str) -> str:
        """
        创建一个带指定标题的新对话，并返回其 ID。
        """
        normalized_title = str(title or "新对话").strip() or "新对话"
        new_conversation = self.create_new_conversation()
        new_conversation["title"] = normalized_title

        data = self._read_data()
        for conversation in data["conversations"]:
            if conversation["id"] == new_conversation["id"]:
                conversation["title"] = normalized_title
                conversation["updated_at"] = datetime.now().isoformat()
                break

        self._write_data(data)
        return new_conversation["id"]

    def save_current_conversation(self, messages: List[Dict], title: Optional[str] = None, conversation_id: Optional[str] = None) -> str:
        """
        保存当前对话

        Args:
            messages: 当前对话的消息列表
            title: 对话标题，可选
            conversation_id: 对话ID，可选

        Returns:
            str: 保存成功的对话ID
        """
        data = self._read_data()
        
        # 查找是否存在当前对话（使用对话ID匹配）
        current_time = datetime.now().isoformat()
        current_conv = None
        
        # 如果提供了对话ID，优先通过ID查找
        if conversation_id:
            for conv in data["conversations"]:
                if conv["id"] == conversation_id:
                    current_conv = conv
                    break
        
        # 如果没有通过ID找到，再尝试通过最后一条消息内容匹配（兼容旧逻辑）
        if not current_conv and messages:
            for conv in data["conversations"]:
                if conv["messages"] and conv["messages"][-1]["content"] == messages[-1]["content"]:
                    current_conv = conv
                    break
        
        if current_conv:
            # 对于当前项目，页面会在 assistant 消息里附加 card_recommendation 等元信息。
            # 因此这里直接覆盖为页面当前完整消息列表，避免只追加新消息时丢失 metadata 更新。
            current_conv["messages"] = messages
            current_conv["updated_at"] = current_time
            if title:
                current_conv["title"] = title
        else:
            # 创建新对话
            conversation_id = f"{self.conversation_type}_conv_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            current_conv = {
                "id": conversation_id,
                "title": title or "新对话",
                "created_at": current_time,
                "updated_at": current_time,
                "messages": messages
            }
            data["conversations"].insert(0, current_conv)
        
        self._write_data(data)
        return current_conv["id"]


    def get_user_conversations(self) -> List[Dict]:
        """
        获取用户的所有对话列表

        Returns:
            List[Dict]: 对话列表，按更新时间倒序排列
        """
        data = self._read_data()
        conversations = data.get("conversations", [])
        # 按更新时间倒序排列
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def load_conversation(self, conversation_id: str) -> Optional[List[Dict]]:
        """
        加载指定对话

        Args:
            conversation_id: 对话ID

        Returns:
            Optional[List[Dict]]: 对话消息列表，如果未找到则返回None
        """
        conversations = self.get_user_conversations()
        for conv in conversations:
            if conv["id"] == conversation_id:
                return conv["messages"]
        return None

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除指定对话

        Args:
            conversation_id: 对话ID

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        data = self._read_data()
        initial_count = len(data["conversations"])
        data["conversations"] = [c for c in data["conversations"] if c["id"] != conversation_id]
        
        if len(data["conversations"]) < initial_count:
            self._write_data(data)
            return True
        return False