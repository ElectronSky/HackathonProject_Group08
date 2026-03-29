"""
数据管理核心类
负责所有用户数据的增删改查操作
"""

#python -m utils.data_handler 使用if name == main

import json
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

try:
    from .path_tools import get_abs_path
    from .config_handler import budget_conf
    from .account_manager import AccountManager
except ImportError:
    from importlib import import_module

    get_abs_path = import_module("utils.path_tools").get_abs_path
    budget_conf = import_module("utils.config_handler").budget_conf
    AccountManager = import_module("utils.account_manager").AccountManager

import uuid


class UserDataManager:
    """
       用户数据管理器

       核心职责：
       - 交易记录的持久化存储（JSON 格式）
       - 多条件查询与筛选
       - 预算管理与统计
       - 数据导入导出
       """

    #初始化这个manager获取用户信息时要传入用户的id
    def __init__(self, user_id: str):
        """
        初始化用户数据管理器

        Args:
            user_id: 用户唯一标识符
        """
        self.user_id = user_id
        self.user_file = get_abs_path(f"data/users/{user_id}/transactions.json")
        self._ensure_user_file_exists()

    def _ensure_user_file_exists(self):
        """确保用户数据文件存在，不存在则创建初始结构"""
        user_dir = os.path.dirname(self.user_file)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        if not os.path.exists(self.user_file):
            initial_data = {
                "user_info": {
                    "user_id": self.user_id,
                    "username": f"用户_{self.user_id}",
                    "created_at": datetime.now().isoformat(),
                    #deleted password here
                },
                "transactions": [],
                "budget_settings": {},
                "custom_categories": []
            }
            self._write_data(initial_data)

    def _build_default_user_info(self, data: Optional[dict] = None) -> dict:
        """
        构建标准化后的用户信息结构。

        说明：
        - 兼容旧数据文件里没有 user_info 的情况；
        - 如旧数据在顶层保留了 user_id / created_at，则优先沿用原值。
        """
        data = data or {}
        return {
            "user_id": data.get("user_id", self.user_id),
            "username": data.get("username", f"用户_{self.user_id}"),
            "created_at": data.get("created_at", datetime.now().isoformat()),
        }

    def _ensure_data_structure(self, data: dict) -> tuple[dict, bool]:
        """
        确保用户数据结构完整。

        Returns:
            tuple[dict, bool]: 标准化后的数据，以及是否发生了结构修正
        """
        has_changed = False

        # 兼容旧版本用户文件缺少 user_info 的情况
        if not isinstance(data.get("user_info"), dict):
            data["user_info"] = self._build_default_user_info(data)
            has_changed = True
        else:
            user_info = data["user_info"]
            if not user_info.get("user_id"):
                user_info["user_id"] = self.user_id
                has_changed = True
            if not user_info.get("username"):
                user_info["username"] = f"用户_{self.user_id}"
                has_changed = True
            if not user_info.get("created_at"):
                user_info["created_at"] = data.get("created_at", datetime.now().isoformat())
                has_changed = True

        # 为后续所有功能补齐稳定字段，避免旧数据文件缺字段时报错
        if not isinstance(data.get("transactions"), list):
            data["transactions"] = []
            has_changed = True

        if not isinstance(data.get("budget_settings"), dict):
            data["budget_settings"] = {}
            has_changed = True

        if not isinstance(data.get("custom_categories"), list):
            data["custom_categories"] = []
            has_changed = True

        return data, has_changed

    def _read_data(self) -> dict:
        """读取用户数据文件"""
        with open(self.user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 对已有用户文件做轻量结构修正，保证新旧数据兼容
        data, has_changed = self._ensure_data_structure(data)
        if has_changed:
            self._write_data(data)

        return data

    def _write_data(self, data: dict):
        """写入用户数据文件"""
        with open(self.user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_transaction(self, transaction_data: dict) -> dict:
        """
        添加单笔交易记录，同时从流动资金扣除支出金额

        Args:
            transaction_data: 交易数据字典

        Returns:
            dict: 完整的交易记录（含生成的 ID）
        """

        #当前用户数据存储在data
        data = self._read_data()

        transaction_id = f"trans_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 获取支出金额
        amount = float(transaction_data["amount"])

        transaction = {
            "transaction_id": transaction_id,
            #如果ai有给时间就给，不然默认给当前年月日
            "date": transaction_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            #"timestamp": datetime.now().isoformat(),
            "category": transaction_data["category"],
            "subcategory": transaction_data.get("subcategory", ""),
            "amount": amount,
            "description": transaction_data.get("description", ""),
            #"payment_method": transaction_data.get("payment_method", "未指定"),
            #"location": transaction_data.get("location", ""),
            #"tags": transaction_data.get("tags", []),
            #"note": transaction_data.get("note", ""),
            #"is_recurring": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        data["transactions"].append(transaction)
        self._write_data(data)
        
        # 支出时从流动资金扣除
        if amount > 0:
            account_manager = AccountManager(self.user_id)
            account_manager.adjust_balance("liquid", -amount)

        return transaction

    def get_all_transactions(self) -> List[dict]:
        """获取所有交易记录"""
        return self._read_data()["transactions"]

    def get_budget_settings(self) -> Dict[str, Dict[str, float]]:
        """
        获取当前用户的预算设置。

        Returns:
            Dict[str, Dict[str, float]]: 按类别分层的预算结构，例如：
            {
                "餐饮": {"weekly": 200.0, "monthly": 800.0},
                "交通": {"monthly": 500.0}
            }
        """
        data = self._read_data()
        return data.get("budget_settings", {})

    def get_budget_warning_threshold(self) -> float:
        """
        获取统一预算预警阈值。

        说明：
        - 阈值来自 config/budget.yml；
        - 当前版本使用统一阈值，不为单个用户或单个类别单独配置；
        - 若配置缺失或非法，则回退到推荐默认值 0.8。
        """
        raw_threshold = budget_conf.get("budget_alert", {}).get("warning_threshold", 0.8)

        try:
            warning_threshold = float(raw_threshold)
        except (TypeError, ValueError):
            return 0.8

        # 预警阈值应位于 0~1 之间，越界时回退到推荐默认值
        if 0 < warning_threshold < 1:
            return warning_threshold
        return 0.8

    def _normalize_reference_date(self, reference_date=None) -> date:
        """
        将参考日期统一转换为 date 对象。

        支持传入：
        - None：默认使用今天；
        - datetime/date：直接转换；
        - YYYY-MM-DD 字符串：解析后转换。
        """
        if reference_date is None:
            return datetime.now().date()

        if isinstance(reference_date, datetime):
            return reference_date.date()

        if isinstance(reference_date, date):
            return reference_date

        if isinstance(reference_date, str):
            return datetime.strptime(reference_date, "%Y-%m-%d").date()

        raise ValueError("reference_date 必须为 None、date、datetime 或 YYYY-MM-DD 字符串")

    def _get_budget_period_range(self, period: str = "monthly", reference_date=None) -> Dict:
        """
        获取预算周期对应的日期范围。

        Args:
            period: weekly 或 monthly
            reference_date: 参考日期，默认今天

        Returns:
            Dict: 包含周期起止日期、周期标签等信息
        """
        normalized_date = self._normalize_reference_date(reference_date)

        if period == "monthly":
            start_date = normalized_date.replace(day=1)
            if normalized_date.month == 12:
                next_month_first_day = normalized_date.replace(year=normalized_date.year + 1, month=1, day=1)
            else:
                next_month_first_day = normalized_date.replace(month=normalized_date.month + 1, day=1)
            end_date = next_month_first_day - timedelta(days=1)
            period_label = start_date.strftime("%Y-%m")
            display_label = f"{period_label} 月"
        elif period == "weekly":
            start_date = normalized_date - timedelta(days=normalized_date.weekday())
            end_date = start_date + timedelta(days=6)
            iso_year, iso_week, _ = normalized_date.isocalendar()
            period_label = f"{iso_year}-W{iso_week:02d}"
            display_label = f"{period_label} 周"
        else:
            raise ValueError("period 仅支持 weekly 或 monthly")

        return {
            "period": period,
            "reference_date": normalized_date,
            "period_label": period_label,
            "display_label": display_label,
            "start_date": start_date,
            "end_date": end_date,
            "start_date_str": start_date.strftime("%Y-%m-%d"),
            "end_date_str": end_date.strftime("%Y-%m-%d"),
        }

    def get_current_period_category_spend(self, period: str = "monthly", reference_date=None) -> Dict[str, float]:
        """
        获取指定预算周期内，各类别当前累计支出。

        Args:
            period: weekly 或 monthly
            reference_date: 参考日期，默认今天

        Returns:
            Dict[str, float]: 类别 -> 当前周期累计金额
        """
        period_range = self._get_budget_period_range(period, reference_date)
        transactions = self.get_transactions_by_filters(
            start_date=period_range["start_date_str"],
            end_date=period_range["end_date_str"]
        )

        category_spend = {}
        for transaction in transactions:
            category_name = str(transaction.get("category", "")).strip()
            if not category_name:
                continue

            category_spend[category_name] = round(
                category_spend.get(category_name, 0.0) + float(transaction.get("amount", 0.0)),
                2
            )

        return category_spend

    def get_budget_progress(self,
                            period: str = "monthly",
                            reference_date=None,
                            warning_threshold: Optional[float] = None) -> List[Dict]:
        """
        获取指定预算周期内，各预算类别的使用进度。

        Returns:
            List[Dict]: 每个元素包含类别、预算、已用、剩余、状态等信息
        """
        threshold = warning_threshold if warning_threshold is not None else self.get_budget_warning_threshold()
        period_range = self._get_budget_period_range(period, reference_date)
        budget_settings = self.get_budget_settings()
        category_spend = self.get_current_period_category_spend(period, reference_date)

        progress_list = []
        status_priority = {
            "over": 0,
            "warning": 1,
            "normal": 2,
        }

        for category_name, category_budget in budget_settings.items():
            if not isinstance(category_budget, dict):
                continue

            if period not in category_budget:
                continue

            budget_amount = float(category_budget[period])
            spent_amount = round(float(category_spend.get(category_name, 0.0)), 2)
            remaining_amount = round(budget_amount - spent_amount, 2)
            over_amount = round(max(0.0, spent_amount - budget_amount), 2)

            # 预算值允许等于 0：表示该类别在当前周期不允许产生支出。
            if budget_amount <= 0:
                usage_ratio = 0.0 if spent_amount <= 0 else 1.0
                status = "over" if spent_amount > 0 else "normal"
            else:
                usage_ratio = round(spent_amount / budget_amount, 4)
                if spent_amount >= budget_amount:
                    status = "over"
                elif spent_amount >= budget_amount * threshold:
                    status = "warning"
                else:
                    status = "normal"

            progress_list.append({
                "category": category_name,
                "period": period,
                "period_label": period_range["period_label"],
                "display_label": period_range["display_label"],
                "reference_date": period_range["reference_date"].strftime("%Y-%m-%d"),
                "start_date": period_range["start_date_str"],
                "end_date": period_range["end_date_str"],
                "budget": round(budget_amount, 2),
                "spent": spent_amount,
                "remaining": remaining_amount,
                "over_amount": over_amount,
                "usage_ratio": usage_ratio,
                "warning_threshold": threshold,
                "warning_amount": round(budget_amount * threshold, 2),
                "status": status,
            })

        progress_list.sort(
            key=lambda item: (
                status_priority.get(item["status"], 99),
                -item["usage_ratio"],
                item["category"]
            )
        )

        return progress_list

    def get_budget_alerts(self,
                          period: str = "monthly",
                          reference_date=None,
                          warning_threshold: Optional[float] = None) -> Dict:
        """
        获取指定预算周期内的预算提醒结果。

        Returns:
            Dict: 包含 over / warning / normal 三类预算状态及统计信息
        """
        progress_list = self.get_budget_progress(
            period=period,
            reference_date=reference_date,
            warning_threshold=warning_threshold
        )

        over_items = [item for item in progress_list if item["status"] == "over"]
        warning_items = [item for item in progress_list if item["status"] == "warning"]
        normal_items = [item for item in progress_list if item["status"] == "normal"]

        period_range = self._get_budget_period_range(period, reference_date)
        threshold = warning_threshold if warning_threshold is not None else self.get_budget_warning_threshold()

        return {
            "period": period,
            "period_label": period_range["period_label"],
            "display_label": period_range["display_label"],
            "reference_date": period_range["reference_date"].strftime("%Y-%m-%d"),
            "warning_threshold": threshold,
            "all": progress_list,
            "over": over_items,
            "warning": warning_items,
            "normal": normal_items,
            "summary": {
                "total_budget_categories": len(progress_list),
                "over_count": len(over_items),
                "warning_count": len(warning_items),
                "normal_count": len(normal_items),
            }
        }

    def get_category_budget_status(self,
                                   category: str,
                                   period: str = "monthly",
                                   reference_date=None,
                                   warning_threshold: Optional[float] = None) -> Optional[Dict]:
        """
        获取某个类别在指定周期内的预算状态。

        Args:
            category: 类别名称
            period: weekly 或 monthly
            reference_date: 参考日期
            warning_threshold: 可选自定义阈值，不传则读取统一配置
        """
        normalized_category = str(category).strip()
        if not normalized_category:
            return None

        for item in self.get_budget_progress(period, reference_date, warning_threshold):
            if item["category"] == normalized_category:
                return item

        return None

    def update_budget_settings(self, budget_settings: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        更新当前用户的预算设置。

        规则：
        - budget_settings 按类别分层存储；
        - 每个类别下仅允许 weekly / monthly 两种周期；
        - 空值不落库；
        - 金额必须为非负数。

        Args:
            budget_settings: 预算配置字典

        Returns:
            Dict[str, Dict[str, float]]: 清洗后并已成功保存的预算配置
        """
        cleaned_budget_settings = {}

        for raw_category, raw_limits in budget_settings.items():
            category_name = str(raw_category).strip()
            if not category_name or not isinstance(raw_limits, dict):
                continue

            cleaned_limits = {}
            for period in ["weekly", "monthly"]:
                raw_value = raw_limits.get(period)

                # 空值表示用户未设置该周期预算，直接跳过即可
                if raw_value in [None, ""]:
                    continue

                numeric_value = float(raw_value)
                if numeric_value < 0:
                    raise ValueError(f"{category_name} 的 {period} 预算不能为负数")

                cleaned_limits[period] = round(numeric_value, 2)

            # 仅当该类别至少设置了一个周期预算时才写入
            if cleaned_limits:
                cleaned_budget_settings[category_name] = cleaned_limits

        data = self._read_data()
        data["budget_settings"] = cleaned_budget_settings
        self._write_data(data)

        return cleaned_budget_settings

    def get_transactions_by_filters(self,
                                    category: Optional[str] = None,
                                    subcategory: Optional[str] = None,
                                    month: Optional[str] = None,
                                    start_date: Optional[str] = None,
                                    end_date: Optional[str] = None
                                    ) -> List[dict]:
        """
        多条件查询交易记录

        Args:
            category: 类别筛选（可选）
            subcategory: 子类别筛选（可选）
            month: 月份筛选（可选，格式 YYYY-MM）
            start_date: 开始日期（可选，格式 YYYY-MM-DD）
            end_date: 结束日期（可选，格式 YYYY-MM-DD）

        Returns:
            List[Dict]: 符合条件的交易记录列表
        """
        data = self._read_data()
        transactions = data["transactions"]

        # 应用筛选条件
        filtered = []
        for t in transactions:
            # 类别筛选
            if category and t["category"] != category:
                continue
            
            # 子类别筛选
            if subcategory and t["subcategory"] != subcategory:
                continue
            
            # 月份筛选
            if month and not t["date"].startswith(month):
                continue
            
            # 日期范围筛选
            if start_date and t["date"] < start_date:
                continue
            if end_date and t["date"] > end_date:
                continue
            
            filtered.append(t)

        return filtered

    #时间线模式依赖方法
    def get_transactions_timeline(self) -> List[Dict]:
        """
        获取按时间分组的交易记录（时间线模式）
        
        Returns:
            List[Dict]: 时间段分组列表，每个元素包含：
                - period: 时间段名称（如"今天"、"昨天"）
                - transactions: 该时间段内的所有交易（已按日期排序）
        """
        from datetime import datetime
        
        all_transactions = self.get_all_transactions()
        
        # 定义时间段顺序（从近到远）
        periods_order = [
            "今天",
            "昨天",
            "前天",
            "一周内",
            "一个月内",
            "一年内",
            "一年前及以上",
        ]
        
        # 初始化分组字典
        grouped = {period: [] for period in periods_order}
        
        # 当前日期
        today = datetime.now().date()
        
        # 遍历所有交易，分配到对应时间段
        for transaction in all_transactions:
            trans_date = datetime.strptime(transaction["date"], "%Y-%m-%d").date()
            days_diff = (today - trans_date).days
            
            # 根据天数差判断时间段
            if days_diff == 0:
                period = "今天"
            elif days_diff == 1:
                period = "昨天"
            elif days_diff == 2:
                period = "前天"
            elif 3 <= days_diff <= 7:
                period = "一周内"
            elif 8 <= days_diff <= 30:
                period = "一个月内"
            elif 30 < days_diff <= 365:
                period = "一年内"
            else:  # days_diff >= 365 或 8-29 天（归入一年前及以上）
                period = "一年前及以上"
            
            grouped[period].append(transaction)
        
        # 对每个时间段内的交易按日期排序（倒序）
        result = []
        for period in periods_order:
            #如果该类别下有交易（只添加有交易的时段）
            if grouped[period]:
                # 对交易按日期排序
                sorted_trans = sorted(
                    grouped[period],
                    key=lambda x: x["date"],
                    reverse=True
                )
                # 添加时间段
                result.append({
                    "period": period,
                    "transactions": sorted_trans
                })
        
        return result

    #传入消费id和新的消费信息，更新该条交易记录
    def update_transaction(self, transaction_id: str, update_data: dict) -> dict:
        data = self._read_data()

        # 找到要更新的记录，获取旧金额
        old_transaction = None
        record_index = None
        for i, t in enumerate(data["transactions"]):
            if t["transaction_id"] == transaction_id:
                old_transaction = t.copy()
                record_index = i
                break
        
        if old_transaction is None:
            raise Exception(f"交易记录不存在：{transaction_id}")
        
        # 获取旧金额和新金额
        old_amount = float(old_transaction.get("amount", 0.0))
        new_amount = float(update_data.get("amount", old_amount))
        
        # 更新交易记录
        for key, value in update_data.items():
            if key in old_transaction and key not in ["transaction_id", "created_at"]:
                data["transactions"][record_index][key] = value

        data["transactions"][record_index]["updated_at"] = datetime.now().isoformat()
        self._write_data(data)
        
        # 调整流动资金差额
        if old_amount != new_amount:
            account_manager = AccountManager(self.user_id)
            # 差额 = 旧金额 - 新金额
            # 如果旧金额更大，说明要增加流动资金（差额为正）
            # 如果新金额更大，说明要减少流动资金（差额为负）
            difference = old_amount - new_amount
            if difference != 0:
                account_manager.adjust_balance("liquid", difference)
        
        return data["transactions"][record_index]

    def get_statistics_by_filter(self,
                               month: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               category: Optional[str] = None,
                               subcategory: Optional[str] = None) -> Dict:
        """
        根据过滤条件获取消费统计数据
        
        Args:
            month: 月份筛选（可选，格式 YYYY-MM）
            start_date: 开始日期（可选，格式 YYYY-MM-DD）
            end_date: 结束日期（可选，格式 YYYY-MM-DD）
            category: 类别筛选（可选）
            subcategory: 子类别筛选（可选）
            
        Returns:
            Dict: 包含各类统计信息的字典，结构如下：
            {
                "category_stats": {  # 按类别统计
                    "餐饮": {"total_amount": 0.0, "count": 0},
                    "交通": {"total_amount": 0.0, "count": 0},
                    # ... 其他类别
                },
                "time_stats": {  # 按时间维度统计
                    "yearly": {"2025": {"total_amount": 0.0, "count": 0}},
                    "monthly": {"2025-01": {"total_amount": 0.0, "count": 0}},
                    "weekly": {"2025-W01": {"total_amount": 0.0, "count": 0}}
                },
                "amount_ratio": {  # 各类别金额占比
                    "餐饮": 0.0,
                    "交通": 0.0,
                    # ... 其他类别
                },
                "time_amount_ratio": {  # 各时间段金额占总金额比例
                    "yearly": {"2025": 0.0},
                    "monthly": {"2025-01": 0.0},
                    "weekly": {"2025-W01": 0.0}
                },
                "amount_level_ratio": {  # 不同金额级别交易数量占比
                    "10元及以下": 0.0,
                    "10到50元": 0.0,
                    "50到100元": 0.0,
                    "100到300元": 0.0,
                    "300到1000元": 0.0,
                    "1000元以上": 0.0
                }
            }
        """
        # 获取符合条件的交易列表
        transactions = self.get_transactions_by_filters(
            category=category,
            subcategory=subcategory,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
        
        # 初始化统计结果
        statistics = {
            "category_stats": {},
            "time_stats": {
                "yearly": {},
                "monthly": {},
                "weekly": {}
            },
            "amount_ratio": {},
            "time_amount_ratio": {
                "yearly": {},
                "monthly": {},
                "weekly": {}
            },
            "amount_level_ratio": {
                "10元及以下": 0,
                "10到50元": 0,
                "50到100元": 0,
                "100到300元": 0,
                "300到1000元": 0,
                "1000元以上": 0
            }
        }
        
        if not transactions:
            return statistics
            
        # 计算总金额和总交易数
        total_amount = sum(t["amount"] for t in transactions)
        total_count = len(transactions)
        
        # 遍历所有交易进行统计
        for transaction in transactions:
            amount = transaction["amount"]
            date_str = transaction["date"]
            category = transaction["category"]
            
            # 1. 按类别统计
            if category not in statistics["category_stats"]:
                statistics["category_stats"][category] = {"total_amount": 0.0, "count": 0}
            statistics["category_stats"][category]["total_amount"] += amount
            statistics["category_stats"][category]["count"] += 1
            
            # 2. 按时间维度统计
            year = date_str[:4]
            month_key = date_str[:7]
            
            # 年度统计
            if year not in statistics["time_stats"]["yearly"]:
                statistics["time_stats"]["yearly"][year] = {"total_amount": 0.0, "count": 0}
            statistics["time_stats"]["yearly"][year]["total_amount"] += amount
            statistics["time_stats"]["yearly"][year]["count"] += 1
            
            # 月度统计
            if month_key not in statistics["time_stats"]["monthly"]:
                statistics["time_stats"]["monthly"][month_key] = {"total_amount": 0.0, "count": 0}
            statistics["time_stats"]["monthly"][month_key]["total_amount"] += amount
            statistics["time_stats"]["monthly"][month_key]["count"] += 1
            
            # 周统计 (使用ISO周格式)
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                week_key = f"{year}-W{date_obj.isocalendar()[1]:02d}"
                if week_key not in statistics["time_stats"]["weekly"]:
                    statistics["time_stats"]["weekly"][week_key] = {"total_amount": 0.0, "count": 0}
                statistics["time_stats"]["weekly"][week_key]["total_amount"] += amount
                statistics["time_stats"]["weekly"][week_key]["count"] += 1
            except:
                pass  # 如果日期解析失败则跳过周统计
                
            # 5. 不同级别金额的交易数量统计
            if amount <= 10:
                statistics["amount_level_ratio"]["10元及以下"] += 1
            elif amount <= 50:
                statistics["amount_level_ratio"]["10到50元"] += 1
            elif amount <= 100:
                statistics["amount_level_ratio"]["50到100元"] += 1
            elif amount <= 300:
                statistics["amount_level_ratio"]["100到300元"] += 1
            elif amount <= 1000:
                statistics["amount_level_ratio"]["300到1000元"] += 1
            else:
                statistics["amount_level_ratio"]["1000元以上"] += 1
        
        # 3. 计算各类别金额占比
        amount_ratio_map: dict[str, float] = statistics["amount_ratio"]
        for category, stats in statistics["category_stats"].items():
            if total_amount > 0:
                amount_ratio_map[category] = round(stats["total_amount"] / total_amount, 4)
            else:
                amount_ratio_map[category] = 0.0
                
        # 4. 计算各时间段金额占总金额比例
        time_amount_ratio_map = statistics["time_amount_ratio"]
        for time_type in ["yearly", "monthly", "weekly"]:
            for period, stats in statistics["time_stats"][time_type].items():
                if total_amount > 0:
                    time_amount_ratio_map[time_type][period] = round(stats["total_amount"] / total_amount, 4)
                else:
                    time_amount_ratio_map[time_type][period] = 0.0
        
        # 6. 转换金额级别统计为占比
        level_ratios: dict[str, float] = {}
        for level, count in statistics["amount_level_ratio"].items():
            if total_count > 0:
                level_ratios[level] = round(float(count) / total_count, 4)
            else:
                level_ratios[level] = 0.0
        statistics["amount_level_ratio"] = level_ratios
        
        # 7. 确保所有统计字段的类型安全，避免后续处理时出现类型错误
        # 确保 category_stats 中的值都是浮点数
        for cat in statistics["category_stats"]:
            stats = statistics["category_stats"][cat]
            if "total_amount" in stats:
                statistics["category_stats"][cat]["total_amount"] = float(stats["total_amount"])
        
        # 确保 time_stats 中的值都是浮点数
        for time_type in statistics["time_stats"]:
            for period in statistics["time_stats"][time_type]:
                stats = statistics["time_stats"][time_type][period]
                if "total_amount" in stats:
                    statistics["time_stats"][time_type][period]["total_amount"] = float(stats["total_amount"])
        
        return statistics

    def delete_transaction(self, transaction_id: str) -> bool:
        """
        删除单笔交易记录，同时将支出金额加回流动资金

        Args:
            transaction_id: 交易 ID

        Returns:
            bool: 删除成功返回 True
        """
        data = self._read_data()
        
        # 找到要删除的交易记录，获取金额
        transaction_to_delete = None
        for t in data["transactions"]:
            if t["transaction_id"] == transaction_id:
                transaction_to_delete = t
                break
        
        original_count = len(data["transactions"])

        data["transactions"] = [
            t for t in data["transactions"]
            if t["transaction_id"] != transaction_id
        ]

        if len(data["transactions"]) < original_count:
            self._write_data(data)
            
            # 删除支出时，将金额加回流动资金
            if transaction_to_delete:
                amount = float(transaction_to_delete.get("amount", 0.0))
                if amount > 0:
                    account_manager = AccountManager(self.user_id)
                    account_manager.adjust_balance("liquid", amount)
            
            return True
        return False




