"""
知识卡片候选预筛器。
负责把财商 evidence pack 转成少量高相关候选卡片，降低后续模型选卡的上下文噪音。
"""

from __future__ import annotations

from typing import Optional

try:
    from .card_repository import CardRepository
    from .card_state_manager import CardStateManager
except ImportError:
    from card_repository import CardRepository
    from card_state_manager import CardStateManager


class CardCandidateBuilder:
    """
    Phase 2 的卡片候选构建器。

    设计原则：
    - 程序先负责做结构化预筛；
    - 只把少量候选交给后续模型做最终选择；
    - 避免所有推荐逻辑都堆在 prompt 里不可控。
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.repository = CardRepository()
        self.state_manager = CardStateManager(user_id)

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

    def _collect_problem_signal_text(self, evidence_pack: dict) -> str:
        texts = []
        for signal in evidence_pack.get("problem_signals", []):
            texts.append(self._normalize_text(signal.get("title")))
            texts.append(self._normalize_text(signal.get("detail")))
        return " ".join(part for part in texts if part)

    def _collect_query_and_sample_text(self, evidence_pack: dict, user_query: str) -> str:
        texts = [self._normalize_text(user_query)]
        for item in evidence_pack.get("sample_transactions", []):
            texts.append(self._normalize_text(item.get("category")))
            texts.append(self._normalize_text(item.get("subcategory")))
            texts.append(self._normalize_text(item.get("description")))

        selected_summary = evidence_pack.get("selected_summary", {})
        for item in selected_summary.get("top_categories", []):
            texts.append(self._normalize_text(item.get("name")))
        for item in selected_summary.get("top_subcategories", []):
            texts.append(self._normalize_text(item.get("name")))

        return " ".join(part for part in texts if part)

    def _get_tracked_card_instances(self) -> dict[str, dict]:
        """
        获取用户当前正在追踪的卡片实例信息。
        返回 {card_id: card_instance} 的字典，方便后续查询状态。
        """
        tracked = {}
        for card in self.state_manager.get_active_cards():
            if card.get("status") in {"active", "snoozed"} and card.get("card_id"):
                tracked[str(card["card_id"])] = card
        return tracked

    def build_candidates(self,
                         evidence_pack: dict,
                         user_query: str,
                         max_candidates: int = 5) -> list[dict]:
        """
        根据 evidence pack 预筛知识卡片候选。
        
        修改说明：
        - 不再直接过滤掉已在学习计划中的卡片；
        - 而是把所有卡片都纳入候选，包括正在学习中的卡片；
        - 这样可以推荐"正在学习的卡片为什么仍然值得再次关注"；
        - 页面展示时会根据 is_already_tracked 字段给出不同提示。
        """
        if not evidence_pack or not evidence_pack.get("data_availability", {}).get("has_transactions"):
            return []

        selected_summary = evidence_pack.get("selected_summary", {})
        transaction_count = int(selected_summary.get("transaction_count", 0) or 0)
        active_days = int(selected_summary.get("active_days", 0) or 0)
        top_categories = {
            self._normalize_text(item.get("name")) for item in selected_summary.get("top_categories", [])
        }
        top_subcategories = {
            self._normalize_text(item.get("name")) for item in selected_summary.get("top_subcategories", [])
        }

        problem_signal_text = self._collect_problem_signal_text(evidence_pack)
        query_and_sample_text = self._collect_query_and_sample_text(evidence_pack, user_query)
        
        # 获取已追踪的卡片实例，用于标记
        tracked_card_instances = self._get_tracked_card_instances()

        candidates = []
        for card in self.repository.load_all_cards():
            # 不再过滤掉已追踪的卡片，而是标记后保留
            is_already_tracked = card.get("card_id") in tracked_card_instances
            tracked_instance = tracked_card_instances.get(card.get("card_id"))

            if transaction_count < int(card.get("minimum_transaction_count", 0) or 0):
                continue

            if active_days < int(card.get("minimum_active_days", 0) or 0):
                continue

            score = 0.0
            reasons = []

            focus_category = self._normalize_text(card.get("focus_category"))
            if focus_category and focus_category in top_categories:
                score += 1.8
                reasons.append(f"focus_category 命中 {card.get('focus_category')}")

            card_subcategories = [
                self._normalize_text(subcategory)
                for subcategory in card.get("focus_subcategories", [])
                if self._normalize_text(subcategory)
            ]
            matched_subcategories = [subcategory for subcategory in card_subcategories if subcategory in top_subcategories]
            if matched_subcategories:
                score += 1.4 + 0.4 * min(len(matched_subcategories), 2)
                reasons.append(f"focus_subcategories 命中 {', '.join(matched_subcategories)}")

            matched_problem_keywords = []
            for keyword in card.get("problem_signal_keywords", []):
                normalized_keyword = self._normalize_text(keyword)
                if normalized_keyword and normalized_keyword in problem_signal_text:
                    matched_problem_keywords.append(keyword)
            if matched_problem_keywords:
                score += 1.8 + 0.3 * min(len(matched_problem_keywords), 2)
                reasons.append(f"problem_signals 命中 {', '.join(matched_problem_keywords[:3])}")

            matched_topic_keywords = []
            for keyword in card.get("topic_keywords", []):
                normalized_keyword = self._normalize_text(keyword)
                if normalized_keyword and normalized_keyword in query_and_sample_text:
                    matched_topic_keywords.append(keyword)
            if matched_topic_keywords:
                score += 0.8 + 0.2 * min(len(matched_topic_keywords), 2)
                reasons.append(f"topic_keywords 命中 {', '.join(matched_topic_keywords[:3])}")

            # 如果已在学习计划中，降低优先度（但仍可推荐）
            if is_already_tracked:
                score *= 0.7  # 降低权重，但仍保留在候选中

            if score <= 0:
                continue

            candidate = {
                "card_id": card.get("card_id"),
                "match_score": round(score, 3),
                "match_reasons": reasons,
                "card_payload": card,
                "is_already_tracked": is_already_tracked,
            }
            
            # 如果已在学习计划中，添加追踪状态信息
            if tracked_instance:
                candidate["tracked_instance"] = {
                    "card_instance_id": tracked_instance.get("card_instance_id"),
                    "status": tracked_instance.get("status"),
                    "next_evaluation_date": tracked_instance.get("next_evaluation_date"),
                    "eval_cycle_days": tracked_instance.get("eval_cycle_days"),
                    "user_action": tracked_instance.get("user_action"),
                }
            
            candidates.append(candidate)

        candidates.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)
        return candidates[:max(1, int(max_candidates or 5))]

