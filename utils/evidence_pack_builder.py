"""
AI 财商助手混合证据包构建器
负责把本地交易、预算和统计信息整理成适合分析的证据包
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

try:
    from .category_service import CategoryService
    from .data_handler import UserDataManager
except ImportError:
    from importlib import import_module

    CategoryService = import_module("utils.category_service").CategoryService
    UserDataManager = import_module("utils.data_handler").UserDataManager


class FinanceEvidencePackBuilder:
    """
    财商分析混合证据包构建器。

    第一版设计目标：
    - 先稳定支持最常见的自然语言分析需求；
    - 不直接把全量原始数据丢给大模型；
    - 在“数据层”和“分析表达层”之间补一层可解释的证据整理逻辑。
    """

    def __init__(self, user_id: str):
        """
        初始化证据包构建器。
        """
        self.user_id = user_id
        self.manager = UserDataManager(user_id)
        self.category_service = CategoryService()

    def build(self, task: dict) -> dict:
        """
        根据结构化任务生成混合证据包。
        """
        time_range = task["time_range"]
        start_date = time_range.get("start_date")
        end_date = time_range.get("end_date")
        focus_category = task.get("focus_category")
        focus_subcategory = task.get("focus_subcategory")

        # 先取当前时间窗口内的所有交易，后面再根据类别聚焦进一步裁剪
        window_transactions = self.manager.get_transactions_by_filters(
            start_date=start_date,
            end_date=end_date,
        )

        # 如果用户没有显式指定时间范围，且默认窗口没有数据，则自动回退到全部历史数据
        used_all_data_fallback = False
        if not window_transactions and not time_range.get("explicit", False):
            window_transactions = self.manager.get_all_transactions()
            used_all_data_fallback = True

        # 如果用户还指定了类别或子类别，就在当前时间窗口内进一步聚焦
        selected_transactions = self._filter_focus_transactions(
            window_transactions,
            focus_category=focus_category,
            focus_subcategory=focus_subcategory,
        )

        # 如果用户指定了类别，但当前窗口内这个类别没有数据，就保留窗口数据用于整体说明
        # 同时让 selected_transactions 回退到 window_transactions，避免分析页面完全空掉。
        focus_data_missing = False
        if (focus_category or focus_subcategory) and not selected_transactions:
            selected_transactions = window_transactions
            focus_data_missing = True

        window_statistics = self._build_statistics(
            start_date=start_date,
            end_date=end_date,
            used_all_data_fallback=used_all_data_fallback,
        )
        selected_statistics = self._build_statistics(
            start_date=start_date,
            end_date=end_date,
            category=focus_category,
            subcategory=focus_subcategory,
            used_all_data_fallback=used_all_data_fallback,
        )

        window_summary = self._build_summary(window_transactions, window_statistics)
        selected_summary = self._build_summary(selected_transactions, selected_statistics)
        comparison_summary = self._build_comparison_summary(
            task=task,
            focus_category=focus_category,
            focus_subcategory=focus_subcategory,
        )
        budget_context = self._build_budget_context(
            task=task,
            focus_category=focus_category,
        )
        problem_signals = self._detect_problem_signals(
            summary=selected_summary,
            comparison_summary=comparison_summary,
            budget_context=budget_context,
        )
        sample_transactions = self._pick_sample_transactions(selected_transactions)

        return {
            "task_meta": {
                "intent": task["intent"],
                "intent_label": task["intent_label"],
                "time_label": time_range["label"],
                "start_date": start_date,
                "end_date": end_date,
                "focus_category": focus_category,
                "focus_subcategory": focus_subcategory,
                "used_all_data_fallback": used_all_data_fallback,
                "focus_data_missing": focus_data_missing,
            },
            "data_availability": {
                "window_transaction_count": len(window_transactions),
                "selected_transaction_count": len(selected_transactions),
                "has_transactions": len(selected_transactions) > 0,
            },
            "window_summary": window_summary,
            "selected_summary": selected_summary,
            "window_statistics": window_statistics,
            "selected_statistics": selected_statistics,
            "comparison_summary": comparison_summary,
            "budget_context": budget_context,
            "problem_signals": problem_signals,
            "sample_transactions": sample_transactions,
        }

    def _build_statistics(self,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          category: Optional[str] = None,
                          subcategory: Optional[str] = None,
                          used_all_data_fallback: bool = False) -> dict:
        """
        优先复用 UserDataManager 的统计能力。

        说明：
        - 如果当前分析窗口因为“默认最近 30 天无数据”而回退到全部历史数据，就直接取全量统计；
        - 否则按当前起止日期、类别、子类别组合筛选统计。
        """
        if used_all_data_fallback:
            return self.manager.get_statistics_by_filter(
                category=category,
                subcategory=subcategory,
            )

        return self.manager.get_statistics_by_filter(
            start_date=start_date,
            end_date=end_date,
            category=category,
            subcategory=subcategory,
        )

    def get_analysis_catalog(self) -> dict:
        """
        获取当前用户可用于解析自然语言查询的类别词典。

        说明：
        - 一级类别优先使用配置文件里的标准类别，再合并历史交易中出现过的类别；
        - 子类别优先使用历史交易中真实出现过的子类别，便于识别“奶茶”“话费”等真实查询词。
        """
        transactions = self.manager.get_all_transactions()
        transaction_categories = [
            transaction.get("category", "")
            for transaction in transactions
            if transaction.get("category")
        ]

        merged_categories = self.category_service.get_merged_category_names(transaction_categories)
        subcategory_to_category = {}

        for transaction in transactions:
            category_name = str(transaction.get("category", "")).strip()
            subcategory_name = str(transaction.get("subcategory", "")).strip()
            if category_name and subcategory_name:
                subcategory_to_category[subcategory_name] = category_name

        for category_item in self.category_service.get_all_categories():
            category_name = str(category_item.get("category", "")).strip()
            for subcategory_name in category_item.get("sub_categories", set()):
                if category_name and subcategory_name:
                    subcategory_to_category[str(subcategory_name).strip()] = category_name

        return {
            "categories": merged_categories,
            "subcategory_to_category": subcategory_to_category,
        }

    def _filter_focus_transactions(self,
                                   transactions: list[dict],
                                   focus_category: Optional[str] = None,
                                   focus_subcategory: Optional[str] = None) -> list[dict]:
        """
        根据当前任务是否聚焦某个类别 / 子类别，对窗口交易做进一步过滤。
        """
        filtered_transactions = transactions

        if focus_category:
            filtered_transactions = [
                transaction for transaction in filtered_transactions
                if str(transaction.get("category", "")).strip() == focus_category
            ]

        if focus_subcategory:
            filtered_transactions = [
                transaction for transaction in filtered_transactions
                if str(transaction.get("subcategory", "")).strip() == focus_subcategory
            ]

        return filtered_transactions

    def _build_summary(self, transactions: list[dict], statistics: Optional[dict] = None) -> dict:
        """
        基于交易列表 + 已有统计结果生成摘要。

        设计原则：
        - 能复用 data_handler 的统计结果，就尽量不重复造轮子；
        - 交易样本仍保留程序自定义整理能力，用于补足子类别、最大单笔等细节。
        """
        statistics = statistics or {}

        if not transactions:
            return {
                "transaction_count": 0,
                "total_amount": 0.0,
                "average_amount": 0.0,
                "active_days": 0,
                "top_categories": [],
                "top_subcategories": [],
                "small_transaction_count": 0,
                "high_value_transaction_count": 0,
                "max_amount": 0.0,
                "amount_level_ratio": {},
                "monthly_trend": [],
                "yearly_trend": [],
            }

        total_amount = round(sum(float(transaction.get("amount", 0.0)) for transaction in transactions), 2)
        transaction_count = len(transactions)
        average_amount = round(total_amount / transaction_count, 2) if transaction_count else 0.0
        active_days = len({transaction.get("date") for transaction in transactions if transaction.get("date")})
        max_amount = round(max(float(transaction.get("amount", 0.0)) for transaction in transactions), 2)

        subcategory_counter = defaultdict(lambda: {"amount": 0.0, "count": 0})

        for transaction in transactions:
            subcategory_name = str(transaction.get("subcategory", "未分类")).strip() or "未分类"
            amount = float(transaction.get("amount", 0.0))

            subcategory_counter[subcategory_name]["amount"] += amount
            subcategory_counter[subcategory_name]["count"] += 1

        category_stats = statistics.get("category_stats", {})
        amount_ratio = statistics.get("amount_ratio", {})
        top_categories = [
            {
                "name": category_name,
                "amount": round(stats["total_amount"], 2),
                "count": stats["count"],
                "ratio": round(amount_ratio.get(category_name, 0.0), 4),
            }
            for category_name, stats in sorted(
                category_stats.items(),
                key=lambda item: item[1]["total_amount"],
                reverse=True,
            )[:5]
        ]

        top_subcategories = [
            {
                "name": subcategory_name,
                "amount": round(stats["amount"], 2),
                "count": stats["count"],
                "ratio": round(stats["count"] / transaction_count, 4) if transaction_count > 0 else 0.0,
            }
            for subcategory_name, stats in sorted(
                subcategory_counter.items(),
                key=lambda item: (item[1]["count"], item[1]["amount"]),
                reverse=True,
            )[:3]
        ]

        small_transaction_threshold = 20.0
        high_value_threshold = max(200.0, average_amount * 3 if average_amount > 0 else 200.0)

        small_transaction_count = sum(
            1 for transaction in transactions
            if float(transaction.get("amount", 0.0)) <= small_transaction_threshold
        )
        high_value_transaction_count = sum(
            1 for transaction in transactions
            if float(transaction.get("amount", 0.0)) >= high_value_threshold
        )

        monthly_trend = self._build_time_trend(
            statistics.get("time_stats", {}).get("monthly", {}),
            statistics.get("time_amount_ratio", {}).get("monthly", {}),
            limit=6,
        )
        yearly_trend = self._build_time_trend(
            statistics.get("time_stats", {}).get("yearly", {}),
            statistics.get("time_amount_ratio", {}).get("yearly", {}),
            limit=3,
        )

        return {
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "average_amount": average_amount,
            "active_days": active_days,
            "top_categories": top_categories,
            "top_subcategories": top_subcategories,
            "small_transaction_count": small_transaction_count,
            "high_value_transaction_count": high_value_transaction_count,
            "max_amount": max_amount,
            "amount_level_ratio": statistics.get("amount_level_ratio", {}),
            "monthly_trend": monthly_trend,
            "yearly_trend": yearly_trend,
        }

    @staticmethod
    def _build_time_trend(time_stats: dict, time_ratio: dict, limit: int = 6) -> list[dict]:
        """
        将 data_handler 的时间统计结果整理成更适合展示的趋势列表。
        """
        trend_list = []
        for period_key in sorted(time_stats.keys()):
            period_stats = time_stats[period_key]
            trend_list.append({
                "period": period_key,
                "total_amount": round(period_stats.get("total_amount", 0.0), 2),
                "count": period_stats.get("count", 0),
                "ratio": round(time_ratio.get(period_key, 0.0), 4),
            })

        return trend_list[-limit:]

    def _build_comparison_summary(self,
                                  task: dict,
                                  focus_category: Optional[str] = None,
                                  focus_subcategory: Optional[str] = None) -> Optional[dict]:
        """
        构建与上一时间窗口的对比摘要。
        """
        previous_range = self._get_previous_range(task["time_range"])
        if previous_range is None:
            return None

        previous_transactions = self.manager.get_transactions_by_filters(
            start_date=previous_range["start_date"],
            end_date=previous_range["end_date"],
        )
        previous_transactions = self._filter_focus_transactions(
            previous_transactions,
            focus_category=focus_category,
            focus_subcategory=focus_subcategory,
        )
        previous_summary = self._build_summary(previous_transactions)

        current_transactions = self.manager.get_transactions_by_filters(
            start_date=task["time_range"].get("start_date"),
            end_date=task["time_range"].get("end_date"),
        )
        current_transactions = self._filter_focus_transactions(
            current_transactions,
            focus_category=focus_category,
            focus_subcategory=focus_subcategory,
        )
        current_summary = self._build_summary(current_transactions)

        previous_total = previous_summary["total_amount"]
        current_total = current_summary["total_amount"]
        previous_count = previous_summary["transaction_count"]
        current_count = current_summary["transaction_count"]

        amount_change = round(current_total - previous_total, 2)
        count_change = current_count - previous_count
        amount_change_ratio = 0.0
        if previous_total > 0:
            amount_change_ratio = round(amount_change / previous_total, 4)

        return {
            "label": previous_range["label"],
            "start_date": previous_range["start_date"],
            "end_date": previous_range["end_date"],
            "current_total": current_total,
            "previous_total": previous_total,
            "amount_change": amount_change,
            "amount_change_ratio": amount_change_ratio,
            "current_count": current_count,
            "previous_count": previous_count,
            "count_change": count_change,
        }

    def _get_previous_range(self, time_range: dict) -> Optional[dict]:
        """
        根据当前时间范围，推导上一对比窗口。
        """
        range_type = time_range.get("type")
        start_date_str = time_range.get("start_date")
        end_date_str = time_range.get("end_date")

        if range_type == "all" or not start_date_str or not end_date_str:
            return None

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if range_type in ["last_month", "this_month"]:
            current_month_first_day = start_date.replace(day=1)
            previous_month_last_day = current_month_first_day - timedelta(days=1)
            previous_year = previous_month_last_day.year
            previous_month = previous_month_last_day.month
            previous_start_date, previous_end_date = self._get_month_range(previous_year, previous_month)
            return {
                "label": f"{previous_year}-{previous_month:02d}",
                "start_date": previous_start_date,
                "end_date": previous_end_date,
            }

        window_days = (end_date - start_date).days + 1
        previous_end_date = start_date - timedelta(days=1)
        previous_start_date = previous_end_date - timedelta(days=window_days - 1)
        return {
            "label": f"前一个 {window_days} 天窗口",
            "start_date": previous_start_date.strftime("%Y-%m-%d"),
            "end_date": previous_end_date.strftime("%Y-%m-%d"),
        }

    def _build_budget_context(self, task: dict, focus_category: Optional[str] = None) -> dict:
        """
        生成预算相关上下文。

        说明：
        - 预算本身仍然由程序计算；
        - AI 在分析时只引用已经算好的预算状态。
        """
        reference_date = task["time_range"].get("end_date") or datetime.now().strftime("%Y-%m-%d")
        monthly_alerts = self.manager.get_budget_alerts(period="monthly", reference_date=reference_date)
        weekly_alerts = self.manager.get_budget_alerts(period="weekly", reference_date=reference_date)

        focus_budget_status = None
        if focus_category:
            focus_budget_status = {
                "monthly": self.manager.get_category_budget_status(
                    category=focus_category,
                    period="monthly",
                    reference_date=reference_date,
                ),
                "weekly": self.manager.get_category_budget_status(
                    category=focus_category,
                    period="weekly",
                    reference_date=reference_date,
                ),
            }

        return {
            "monthly": monthly_alerts,
            "weekly": weekly_alerts,
            "focus_category_status": focus_budget_status,
        }

    def _detect_problem_signals(self,
                                summary: dict,
                                comparison_summary: Optional[dict],
                                budget_context: dict) -> list[dict]:
        """
        从统计结果里提取多维度"问题信号"。

        扩充后的检测维度：
        1. 单一类别占比过高
        2. 高频小额非必要消费
        3. 大额单笔支出
        4. 某类子类别消费频率异常
        5. 支出较上期明显上升/下降
        6. 预算超支/预警
        7. 高价值消费占比异常
        8. 日均消费过高
        9. 消费集中度（少数天数占比过高）
        """
        problem_signals = []
        transaction_count = summary["transaction_count"]
        total_amount = summary["total_amount"]
        active_days = summary["active_days"]

        if transaction_count == 0 or total_amount <= 0:
            return problem_signals

        # ========== 1. 单一类别占比过高 ==========
        top_categories = summary["top_categories"]
        if top_categories:
            top_category = top_categories[0]
            if top_category["ratio"] >= 0.45 and top_category["count"] >= 3:
                problem_signals.append({
                    "title": "单一类别支出占比较高",
                    "severity": "high",
                    "detail": f"{top_category['name']} 占当前分析范围总支出的 {top_category['ratio'] * 100:.1f}%（共 {top_category['count']} 笔，¥{top_category['amount']:.2f}），超过建议阈值40%。",
                    "signal_type": "category_concentration",
                })
            # 检测第二、第三类别占比
            for i, cat in enumerate(top_categories[1:3], start=2):
                if cat["ratio"] >= 0.25 and cat["count"] >= 3:
                    problem_signals.append({
                        "title": f"第{i}大类别支出也偏高",
                        "severity": "medium",
                        "detail": f"{cat['name']} 占 {cat['ratio'] * 100:.1f}%（共 {cat['count']} 笔，¥{cat['amount']:.2f}），建议关注是否合理。",
                        "signal_type": "category_concentration",
                    })

        # ========== 2. 高频小额非必要消费 ==========
        small_threshold = 20.0
        small_transactions = [t for t in summary.get("top_subcategories", []) 
                             if t["name"] in ["奶茶", "咖啡", "零食", "饮料", "外卖", "打车", "公交"]]
        if small_transactions:
            total_small_amount = sum(st["amount"] for st in small_transactions)
            total_small_count = sum(st["count"] for st in small_transactions)
            if total_small_count >= 8:
                problem_signals.append({
                    "title": "高频小额非必要消费偏多",
                    "severity": "medium",
                    "detail": f"奶茶/零食/外卖等小额高频消费共 {total_small_count} 笔，金额 ¥{total_small_amount:.2f}。这类消费容易被忽视但长期累积显著。",
                    "signal_type": "impulse_spending",
                })

        small_ratio = summary["small_transaction_count"] / transaction_count if transaction_count > 0 else 0.0
        if summary["small_transaction_count"] >= 5 and small_ratio >= 0.5:
            problem_signals.append({
                "title": "小额支出占比过高",
                "severity": "medium",
                "detail": f"金额不超过 20 元的消费共 {summary['small_transaction_count']} 笔，占总交易数的 {small_ratio * 100:.1f}%。",
                "signal_type": "spending_pattern",
            })

        # ========== 3. 大额单笔支出 ==========
        high_threshold = 200.0
        if summary["high_value_transaction_count"] >= 1 and summary["max_amount"] >= high_threshold:
            problem_signals.append({
                "title": "存在大额单笔支出",
                "severity": "medium",
                "detail": f"当前分析范围内最高单笔支出为 ¥{summary['max_amount']:.2f}，建议确认这笔支出是否在计划内。",
                "signal_type": "large_expense",
            })
        # 大额消费占比
        amount_level_ratio = summary.get("amount_level_ratio", {})
        if amount_level_ratio:
            large_ratio = amount_level_ratio.get("large", 0.0)
            if large_ratio >= 0.3 and summary["high_value_transaction_count"] >= 3:
                problem_signals.append({
                    "title": "大额支出占比偏高",
                    "severity": "high",
                    "detail": f"金额超过 100 元的大额消费占比 {large_ratio * 100:.1f}%（共 {summary['high_value_transaction_count']} 笔），可能导致整体支出超出预期。",
                    "signal_type": "large_expense",
                })

        # ========== 4. 子类别消费频率异常 ==========
        top_subcategories = summary["top_subcategories"]
        if top_subcategories:
            top_subcategory = top_subcategories[0]
            if top_subcategory["count"] >= 5 and top_subcategory["ratio"] >= 0.25:
                problem_signals.append({
                    "title": f"「{top_subcategory['name']}」消费频率过高",
                    "severity": "medium",
                    "detail": f"子类别 {top_subcategory['name']} 共出现 {top_subcategory['count']} 次，占总交易数的 {top_subcategory['ratio'] * 100:.1f}%，金额 ¥{top_subcategory['amount']:.2f}。",
                    "signal_type": "frequency_anomaly",
                })
            # 检测多个子类别同时高频
            high_freq_subcats = [s for s in top_subcategories if s["count"] >= 4]
            if len(high_freq_subcats) >= 2:
                subcat_names = "、".join([s["name"] for s in high_freq_subcats[:3]])
                problem_signals.append({
                    "title": "多个子类别消费频率偏高",
                    "severity": "medium",
                    "detail": f"以下子类别出现频率较高：{subcat_names}。建议评估这些消费是否都有必要。",
                    "signal_type": "frequency_anomaly",
                })

        # ========== 5. 支出较上期明显变化 ==========
        if comparison_summary and comparison_summary["previous_total"] > 0:
            amount_change_ratio = comparison_summary["amount_change_ratio"]
            amount_change = comparison_summary["amount_change"]
            
            if amount_change_ratio >= 0.25 and amount_change >= 50:
                problem_signals.append({
                    "title": "支出较上期明显上升",
                    "severity": "high",
                    "detail": f"与 {comparison_summary['label']} 相比，当前支出增加了 ¥{abs(amount_change):.2f}（涨幅约 {amount_change_ratio * 100:.1f}%），建议分析原因并适当控制。",
                    "signal_type": "trend_change",
                })
            elif amount_change_ratio <= -0.20 and abs(amount_change) >= 30:
                problem_signals.append({
                    "title": "支出较上期有所下降",
                    "severity": "low",
                    "detail": f"与 {comparison_summary['label']} 相比，当前支出减少了 ¥{abs(amount_change):.2f}（降幅约 {abs(amount_change_ratio) * 100:.1f}%），继续保持！",
                    "signal_type": "positive_trend",
                })
            
            # 交易笔数变化
            count_change = comparison_summary.get("count_change", 0)
            if count_change >= 5:
                problem_signals.append({
                    "title": "消费频次明显增加",
                    "severity": "medium",
                    "detail": f"与上期相比，交易笔数增加了 {count_change} 笔。频次增加可能是消费习惯变化的信号。",
                    "signal_type": "frequency_change",
                })

        # ========== 6. 预算超支/预警 ==========
        monthly_summary = budget_context["monthly"]["summary"]
        weekly_summary = budget_context["weekly"]["summary"]
        
        if monthly_summary["over_count"] > 0 or weekly_summary["over_count"] > 0:
            over_categories = []
            # monthly_summary["over"] 和 weekly_summary["over"] 是列表，可以遍历获取具体类别
            for alert in monthly_summary.get("over", []):
                if alert.get("category"):
                    over_categories.append(f"{alert.get('category')}（超¥{alert.get('over_amount', 0):.2f}）")
            problem_signals.append({
                "title": "存在预算超额",
                "severity": "high",
                "detail": f"本月超额类别：{monthly_summary['over_count']} 个；本周超额类别：{weekly_summary['over_count']} 个。具体：{'、'.join(over_categories[:3]) if over_categories else '详见预算页面'}。",
                "signal_type": "budget_over",
            })
        elif monthly_summary["warning_count"] > 0 or weekly_summary["warning_count"] > 0:
            problem_signals.append({
                "title": "存在预算预警",
                "severity": "medium",
                "detail": f"本月 {monthly_summary['warning_count']} 个类别接近预算上限，本周 {weekly_summary['warning_count']} 个类别有预警，建议关注。",
                "signal_type": "budget_warning",
            })

        # ========== 7. 日均消费过高 ==========
        if active_days > 0:
            daily_avg = total_amount / active_days
            if daily_avg >= 150:
                problem_signals.append({
                    "title": "日均消费偏高",
                    "severity": "high",
                    "detail": f"当前分析范围内日均消费 ¥{daily_avg:.2f}（总支出 ¥{total_amount:.2f} / {active_days} 天），对于学生或刚入职的年轻人来说偏高。",
                    "signal_type": "amount_anomaly",
                })
            elif daily_avg >= 100:
                problem_signals.append({
                    "title": "日均消费处于中等水平",
                    "severity": "low",
                    "detail": f"当前日均消费 ¥{daily_avg:.2f}，建议保持或尝试降低到 ¥80 以下。",
                    "signal_type": "amount_anomaly",
                })

        # ========== 8. 平均每笔金额异常 ==========
        avg_amount = summary["average_amount"]
        if avg_amount >= 100:
            problem_signals.append({
                "title": "平均每笔消费偏高",
                "severity": "medium",
                "detail": f"当前平均每笔消费 ¥{avg_amount:.2f}，建议关注大额支出的必要性。",
                "signal_type": "amount_anomaly",
            })
        elif avg_amount <= 10 and transaction_count >= 20:
            problem_signals.append({
                "title": "平均每笔金额偏低",
                "severity": "low",
                "detail": f"当前平均每笔消费仅 ¥{avg_amount:.2f}，多为小额高频消费，容易累积成较大支出。",
                "signal_type": "spending_pattern",
            })

        return problem_signals

    def _pick_sample_transactions(self, transactions: list[dict], limit: int = 6) -> list[dict]:
        """
        抽取少量具有代表性的交易样本。

        设计思路：
        - 同时保留“金额较高”的样本和“最近发生”的样本；
        - 避免把所有明细都塞进上下文，控制证据长度；
        - 让 AI 有足够的细节可以引用。
        """
        if not transactions:
            return []

        sorted_by_amount = sorted(
            transactions,
            key=lambda transaction: float(transaction.get("amount", 0.0)),
            reverse=True,
        )[:3]
        sorted_by_date = sorted(
            transactions,
            key=lambda transaction: (transaction.get("date", ""), float(transaction.get("amount", 0.0))),
            reverse=True,
        )[:3]

        sample_map = {}
        for transaction in sorted_by_amount + sorted_by_date:
            sample_map[transaction.get("transaction_id")] = {
                "date": transaction.get("date"),
                "category": transaction.get("category"),
                "subcategory": transaction.get("subcategory"),
                "amount": round(float(transaction.get("amount", 0.0)), 2),
                "description": transaction.get("description", ""),
            }

        return list(sample_map.values())[:limit]

    @staticmethod
    def _get_month_range(target_year: int, target_month: int) -> tuple[str, str]:
        """
        计算某个月份的完整起止日期。
        """
        last_day = calendar.monthrange(target_year, target_month)[1]
        start_date = datetime(target_year, target_month, 1).strftime("%Y-%m-%d")
        end_date = datetime(target_year, target_month, last_day).strftime("%Y-%m-%d")
        return start_date, end_date


if __name__ == "__main__":
    builder = FinanceEvidencePackBuilder("user_001")
    catalog = builder.get_analysis_catalog()
    print(catalog)

