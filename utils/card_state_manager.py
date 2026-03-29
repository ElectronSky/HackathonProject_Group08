"""
知识卡片状态管理器。
负责把用户对卡片的动作、追踪状态、评估历史持久化到本地 JSON。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

try:
    from .path_tools import get_abs_path
except ImportError:
    from path_tools import get_abs_path


class CardStateManager:
    """
    用户知识卡片状态存储层。

    当前阶段设计：
    - 每个用户一个 JSON 文件；
    - `active_cards` 同时容纳 active / snoozed 两类“仍在追踪中的卡片”；
    - `archived_cards` 存放 completed / archived 的历史卡片，方便后续回看。
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state_dir = get_abs_path("data/knowledge/card_state")
        self.state_file = os.path.join(self.state_dir, f"{user_id}_card_state.json")
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self) -> None:
        if not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir)

        if not os.path.exists(self.state_file):
            self._write_state(self._build_default_state())

    def _build_default_state(self) -> dict:
        return {
            "user_id": self.user_id,
            "active_cards": [],
            "archived_cards": [],
        }

    def _read_state(self) -> dict:
        with open(self.state_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            data = self._build_default_state()

        if not isinstance(data.get("active_cards"), list):
            data["active_cards"] = []
        if not isinstance(data.get("archived_cards"), list):
            data["archived_cards"] = []
        if not data.get("user_id"):
            data["user_id"] = self.user_id

        return data

    def _write_state(self, data: dict) -> None:
        with open(self.state_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def get_state(self) -> dict:
        return self._read_state()

    def get_active_cards(self) -> list[dict]:
        return list(self._read_state().get("active_cards", []))

    def get_archived_cards(self) -> list[dict]:
        return list(self._read_state().get("archived_cards", []))

    def get_all_tracked_cards(self) -> list[dict]:
        state = self._read_state()
        return list(state.get("active_cards", [])) + list(state.get("archived_cards", []))

    def add_active_card(self, card_instance: dict) -> None:
        data = self._read_state()
        data["active_cards"].insert(0, card_instance)
        self._write_state(data)

    def add_archived_card(self, card_instance: dict) -> None:
        data = self._read_state()
        data["archived_cards"].insert(0, card_instance)
        self._write_state(data)

    def get_card_instance(self, card_instance_id: str) -> Optional[dict]:
        for card in self.get_all_tracked_cards():
            if card.get("card_instance_id") == card_instance_id:
                return card
        return None

    def find_existing_card_instance(self, card_id: str, source_conversation_id: Optional[str] = None) -> Optional[dict]:
        """
        根据卡片 id + 来源对话，查找当前是否已经记录过同一张推荐卡片。
        """
        normalized_card_id = str(card_id or "").strip()
        normalized_source_id = str(source_conversation_id or "").strip()

        for card in self.get_all_tracked_cards():
            if card.get("card_id") != normalized_card_id:
                continue
            if normalized_source_id and card.get("source_conversation_id") != normalized_source_id:
                continue
            return card
        return None

    def update_card_action(self, card_instance_id: str, user_action: str) -> None:
        data = self._read_state()
        for group_name in ["active_cards", "archived_cards"]:
            for card in data[group_name]:
                if card.get("card_instance_id") == card_instance_id:
                    card["user_action"] = user_action
                    card["updated_at"] = datetime.now().isoformat()
                    self._write_state(data)
                    return

    def get_due_evaluation_cards(self, reference_date: str) -> list[dict]:
        due_cards = []
        reference_dt = datetime.strptime(reference_date, "%Y-%m-%d").date()

        for card in self.get_active_cards():
            if card.get("status") != "active":
                continue

            next_evaluation_date = card.get("next_evaluation_date")
            if not next_evaluation_date:
                continue

            next_dt = datetime.strptime(next_evaluation_date, "%Y-%m-%d").date()
            if next_dt <= reference_dt:
                due_cards.append(card)

        due_cards.sort(key=lambda item: item.get("next_evaluation_date", "9999-12-31"))
        return due_cards

    def update_next_evaluation(self,
                               card_instance_id: str,
                               next_evaluation_date: str,
                               evaluation_result: dict) -> None:
        data = self._read_state()
        for card in data["active_cards"]:
            if card.get("card_instance_id") != card_instance_id:
                continue

            card["status"] = "active"
            card["next_evaluation_date"] = next_evaluation_date
            card["last_evaluation_result"] = evaluation_result
            card.setdefault("evaluation_history", []).append({
                **evaluation_result,
                "evaluated_at": datetime.now().isoformat(),
            })
            card["updated_at"] = datetime.now().isoformat()
            self._write_state(data)
            return

    def mark_card_completed(self, card_instance_id: str, evaluation_result: dict) -> None:
        data = self._read_state()
        remaining_cards = []
        completed_card = None

        for card in data["active_cards"]:
            if card.get("card_instance_id") == card_instance_id:
                completed_card = card
            else:
                remaining_cards.append(card)

        if completed_card is None:
            return

        completed_card["status"] = "completed"
        completed_card["last_evaluation_result"] = evaluation_result
        completed_card.setdefault("evaluation_history", []).append({
            **evaluation_result,
            "evaluated_at": datetime.now().isoformat(),
        })
        completed_card["completed_at"] = datetime.now().isoformat()
        completed_card["updated_at"] = datetime.now().isoformat()

        data["active_cards"] = remaining_cards
        data["archived_cards"].insert(0, completed_card)
        self._write_state(data)

    def snooze_card(self,
                    card_instance_id: str,
                    next_evaluation_date: str,
                    evaluation_result: Optional[dict] = None) -> None:
        data = self._read_state()
        for card in data["active_cards"]:
            if card.get("card_instance_id") != card_instance_id:
                continue

            card["status"] = "snoozed"
            card["next_evaluation_date"] = next_evaluation_date
            if evaluation_result is not None:
                card["last_evaluation_result"] = evaluation_result
                card.setdefault("evaluation_history", []).append({
                    **evaluation_result,
                    "evaluated_at": datetime.now().isoformat(),
                })
            card["updated_at"] = datetime.now().isoformat()
            self._write_state(data)
            return

    def record_card_action(self,
                           card_payload: dict,
                           user_action: str,
                           source_conversation_id: str,
                           source_query: str,
                           activated_by_time_label: str,
                           eval_cycle_days: int) -> dict:
        """
        根据用户动作创建并落库一条卡片实例。
        """
        existing_instance = self.find_existing_card_instance(
            card_id=card_payload.get("card_id", ""),
            source_conversation_id=source_conversation_id,
        )
        if existing_instance:
            return existing_instance

        normalized_eval_days = max(int(eval_cycle_days or 7), 1)
        today = datetime.now().date()
        next_evaluation_date = (today + timedelta(days=normalized_eval_days)).strftime("%Y-%m-%d")

        status = "active"
        target_collection = "active"
        if user_action == "remind_later":
            status = "snoozed"
        elif user_action == "view_only":
            status = "archived"
            target_collection = "archived"
            next_evaluation_date = None

        card_instance = {
            "card_instance_id": f"inst_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "card_id": card_payload.get("card_id"),
            "card_title": card_payload.get("title"),
            "card_snapshot": card_payload,
            "source_conversation_id": source_conversation_id,
            "source_query": source_query,
            "activated_at": datetime.now().isoformat(),
            "activated_by_report_time_label": activated_by_time_label,
            "status": status,
            "user_action": user_action,
            "eval_cycle_days": normalized_eval_days,
            "next_evaluation_date": next_evaluation_date,
            "last_evaluation_result": None,
            "evaluation_history": [],
            "note": "",  # 用户学习笔记
            "note_updated_at": None,  # 笔记最后更新时间
            "updated_at": datetime.now().isoformat(),
        }

        if target_collection == "active":
            self.add_active_card(card_instance)
        else:
            self.add_archived_card(card_instance)

        return card_instance

    def update_card_status(self, card_instance_id: str, new_status: str) -> bool:
        """
        修改卡片状态（用于用户在卡片页面手动切换状态）。
        
        支持的状态切换：
        - active <-> snoozed（正在学习 ↔ 稍后提醒）
        - active/snoozed -> archived（移入历史）
        """
        valid_statuses = ["active", "snoozed", "archived", "completed"]
        if new_status not in valid_statuses:
            return False

        data = self._read_state()
        
        # 先从 active_cards 找
        for i, card in enumerate(data["active_cards"]):
            if card.get("card_instance_id") == card_instance_id:
                old_status = card.get("status")
                
                # 如果要移入 archived，需要处理
                if new_status in ["archived", "completed"]:
                    card["status"] = new_status
                    card["updated_at"] = datetime.now().isoformat()
                    if new_status == "archived":
                        card["archived_at"] = datetime.now().isoformat()
                    elif new_status == "completed":
                        card["completed_at"] = datetime.now().isoformat()
                    
                    # 从 active_cards 移除
                    moved_card = data["active_cards"].pop(i)
                    # 添加到 archived_cards
                    data["archived_cards"].insert(0, moved_card)
                else:
                    # 在 active 和 snoozed 之间切换
                    card["status"] = new_status
                    card["updated_at"] = datetime.now().isoformat()
                
                self._write_state(data)
                return True
        
        # 再从 archived_cards 找（可能需要恢复为 active）
        for i, card in enumerate(data["archived_cards"]):
            if card.get("card_instance_id") == card_instance_id:
                if new_status == "active":
                    # 从 archived 恢复到 active
                    card["status"] = "active"
                    card["updated_at"] = datetime.now().isoformat()
                    
                    # 从 archived_cards 移除
                    restored_card = data["archived_cards"].pop(i)
                    # 添加到 active_cards
                    data["active_cards"].insert(0, restored_card)
                    self._write_state(data)
                    return True
                elif new_status == "snoozed":
                    # 允许从 archived 切换到 snoozed
                    card["status"] = "snoozed"
                    card["updated_at"] = datetime.now().isoformat()
                    self._write_state(data)
                    return True
        
        return False

    def update_card_note(self, card_instance_id: str, note: str) -> bool:
        """
        更新卡片的学习笔记。
        
        Args:
            card_instance_id: 卡片实例ID
            note: 用户输入的笔记内容
        
        Returns:
            bool: 更新是否成功
        """
        data = self._read_state()
        
        # 在所有卡片中查找
        for group_name in ["active_cards", "archived_cards"]:
            for card in data[group_name]:
                if card.get("card_instance_id") == card_instance_id:
                    card["note"] = str(note).strip()
                    card["note_updated_at"] = datetime.now().isoformat()
                    card["updated_at"] = datetime.now().isoformat()
                    self._write_state(data)
                    return True
        
        return False

    def get_card_note(self, card_instance_id: str) -> tuple[str, str]:
        """
        获取卡片的笔记内容。
        
        Returns:
            tuple: (note, note_updated_at)
        """
        data = self._read_state()
        
        for group_name in ["active_cards", "archived_cards"]:
            for card in data[group_name]:
                if card.get("card_instance_id") == card_instance_id:
                    return (
                        card.get("note", ""),
                        card.get("note_updated_at", "")
                    )
        
        return "", ""

