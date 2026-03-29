"""
知识卡片仓库。
负责读取本地卡片库，并为推荐链 / 评估链提供稳定的数据访问入口。
"""

from __future__ import annotations

import json
import os
from typing import Optional

try:
    from .path_tools import get_abs_path
except ImportError:
    from path_tools import get_abs_path


class CardRepository:
    """
    知识卡片读取层。

    设计说明：
    - Phase 2 先把卡片固化在本地 JSON 中；
    - 程序负责读取与校验，agent 不直接碰文件路径；
    - 后续如果卡片改成数据库，这一层也能保持对上层接口稳定。
    """

    def __init__(self, cards_file_path: Optional[str] = None):
        self.cards_file_path = cards_file_path or get_abs_path("data/knowledge/cards/cards_v1.json")

    def load_all_cards(self) -> list[dict]:
        """
        加载全部卡片，并做最小结构清洗。
        """
        if not os.path.exists(self.cards_file_path):
            return []

        with open(self.cards_file_path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)

        cards = raw_data if isinstance(raw_data, list) else raw_data.get("cards", [])
        normalized_cards = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            if not card.get("card_id") or not card.get("title"):
                continue

            normalized_cards.append({
                "card_id": str(card.get("card_id", "")).strip(),
                "title": str(card.get("title", "")).strip(),
                "tags": list(card.get("tags", [])),
                "topic_keywords": list(card.get("topic_keywords", [])),
                "problem_signal_keywords": list(card.get("problem_signal_keywords", [])),
                "focus_category": (str(card.get("focus_category", "")).strip() or None),
                "focus_subcategories": list(card.get("focus_subcategories", [])),
                "minimum_transaction_count": int(card.get("minimum_transaction_count", 0) or 0),
                "minimum_active_days": int(card.get("minimum_active_days", 0) or 0),
                "recommended_eval_days": int(card.get("recommended_eval_days", 7) or 7),
                "doing_text": str(card.get("doing_text", "")).strip(),
                "why_text": str(card.get("why_text", "")).strip(),
                "professional_term": str(card.get("professional_term", "")).strip(),
                "authority_source": str(card.get("authority_source", "")).strip(),
                "trigger_description": str(card.get("trigger_description", "")).strip(),
                "evaluation_description": str(card.get("evaluation_description", "")).strip(),
                "improvement_hint": str(card.get("improvement_hint", "")).strip(),
            })

        return normalized_cards

    def get_card_by_id(self, card_id: str) -> Optional[dict]:
        """
        按 card_id 返回原始卡片内容。
        """
        normalized_card_id = str(card_id or "").strip()
        if not normalized_card_id:
            return None

        for card in self.load_all_cards():
            if card.get("card_id") == normalized_card_id:
                return card
        return None

