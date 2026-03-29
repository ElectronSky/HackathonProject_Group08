"""
收入记录管理器
负责管理收入记录的增删改查和统计功能
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict

try:
    from .path_tools import get_abs_path
    from .account_manager import AccountManager
except ImportError:
    from importlib import import_module
    get_abs_path = import_module("utils.path_tools").get_abs_path
    AccountManager = import_module("utils.account_manager").AccountManager


class IncomeManager:
    """
    收入记录管理器。
    
    职责：
    - 管理收入记录的增删改查
    - 提供收入统计功能
    - 与储蓄账户联动
    """
    
    def __init__(self, user_id: str):
        """
        初始化收入管理器。
        
        Args:
            user_id: 用户唯一标识符
        """
        self.user_id = user_id
        self.income_file = get_abs_path(f"data/users/{user_id}/income_records.json")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保收入文件存在，不存在则创建初始结构"""
        income_dir = os.path.dirname(self.income_file)
        if not os.path.exists(income_dir):
            os.makedirs(income_dir)
        
        if not os.path.exists(self.income_file):
            initial_data = {
                "user_id": self.user_id,
                "income_records": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._write_data(initial_data)
    
    def _read_data(self) -> dict:
        """
        读取收入数据文件。
        
        Returns:
            dict: 收入数据
        """
        with open(self.income_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def _write_data(self, data: dict) -> None:
        """
        写入收入数据文件。
        
        Args:
            data: 收入数据字典
        """
        data["updated_at"] = datetime.now().isoformat()
        with open(self.income_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_income(self, income_data: dict) -> dict:
        """
        添加收入记录。
        
        Args:
            income_data: 收入数据字典，包含以下字段：
                - category: 收入来源（如"工资"、"兼职"）
                - subcategory: 子类别（可选）
                - amount: 收入金额
                - description: 描述（可选）
                - date: 日期（可选，默认今天）
                - savings_amount: 存入储蓄的金额
                - liquid_amount: 进入流动资金的金额
        
        Returns:
            dict: 完整的收入记录（含生成的 ID）
        """
        data = self._read_data()
        
        # 生成收入记录 ID
        income_id = f"income_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 构建收入记录
        income_record = {
            "transaction_id": income_id,
            "date": income_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "category": income_data.get("category", ""),
            "subcategory": income_data.get("subcategory", ""),
            "amount": float(income_data.get("amount", 0.0)),
            "description": income_data.get("description", ""),
            "savings_amount": float(income_data.get("savings_amount", 0.0)),
            "liquid_amount": float(income_data.get("liquid_amount", 0.0)),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # 添加到收入记录列表
        data["income_records"].append(income_record)
        self._write_data(data)
        
        return income_record
    
    def get_all_income(self) -> List[dict]:
        """
        获取所有收入记录。
        
        Returns:
            List[dict]: 所有收入记录列表
        """
        data = self._read_data()
        return data.get("income_records", [])
    
    def get_income_by_filters(self,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            category: Optional[str] = None) -> List[dict]:
        """
        按条件筛选收入记录。
        
        Args:
            start_date: 开始日期（可选，格式 YYYY-MM-DD）
            end_date: 结束日期（可选，格式 YYYY-MM-DD）
            category: 收入来源筛选（可选）
        
        Returns:
            List[dict]: 符合条件的收入记录列表
        """
        all_income = self.get_all_income()
        
        filtered = []
        for record in all_income:
            # 日期范围筛选
            if start_date and record["date"] < start_date:
                continue
            if end_date and record["date"] > end_date:
                continue
            
            # 收入来源筛选
            if category and record["category"] != category:
                continue
            
            filtered.append(record)
        
        return filtered
    
    def get_income_summary(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        """
        获取收入统计摘要。
        
        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        
        Returns:
            dict: 收入统计摘要，包含：
                - total: 收入总额
                - count: 收入记录数
                - by_source: 按收入来源分布
                - savings_total: 存入储蓄总额
                - liquid_total: 进入流动资金总额
        """
        filtered_income = self.get_income_by_filters(start_date=start_date, end_date=end_date)
        
        total = 0.0
        by_source = {}
        savings_total = 0.0
        liquid_total = 0.0
        
        for record in filtered_income:
            amount = float(record.get("amount", 0.0))
            total += amount
            
            # 按来源统计
            source = record.get("category", "其他")
            by_source[source] = by_source.get(source, 0.0) + amount
            
            # 分配金额统计
            savings_total += float(record.get("savings_amount", 0.0))
            liquid_total += float(record.get("liquid_amount", 0.0))
        
        return {
            "total": round(total, 2),
            "count": len(filtered_income),
            "by_source": {k: round(v, 2) for k, v in by_source.items()},
            "savings_total": round(savings_total, 2),
            "liquid_total": round(liquid_total, 2),
        }
    
    def get_income_categories(self) -> List[str]:
        """
        获取已使用的收入来源列表。
        
        Returns:
            List[str]: 收入来源列表
        """
        all_income = self.get_all_income()
        categories = set()
        for record in all_income:
            if record.get("category"):
                categories.add(record["category"])
        return sorted(list(categories))
    
    def delete_income(self, transaction_id: str) -> bool:
        """
        删除收入记录，同时回滚储蓄和流动资金。
        
        Args:
            transaction_id: 收入记录 ID
        
        Returns:
            bool: 删除成功返回 True
        """
        data = self._read_data()
        
        # 找到要删除的记录，获取储蓄和流动资金金额
        income_to_delete = None
        for record in data["income_records"]:
            if record["transaction_id"] == transaction_id:
                income_to_delete = record
                break
        
        if not income_to_delete:
            return False
        
        # 回滚账户：从储蓄扣除savings_amount，从流动资金扣除liquid_amount
        account_manager = AccountManager(self.user_id)
        
        savings_amount = float(income_to_delete.get("savings_amount", 0.0))
        liquid_amount = float(income_to_delete.get("liquid_amount", 0.0))
        
        # 如果有储蓄金额，从储蓄账户扣除
        if savings_amount > 0:
            account_manager.adjust_balance("savings", -savings_amount)
        
        # 如果有流动资金金额，从流动资金扣除
        if liquid_amount > 0:
            account_manager.adjust_balance("liquid", -liquid_amount)
        
        # 删除收入记录
        data["income_records"] = [
            record for record in data["income_records"]
            if record["transaction_id"] != transaction_id
        ]
        
        self._write_data(data)
        return True
    
    def update_income(self, transaction_id: str, update_data: dict) -> dict:
        """
        修改收入记录，同时调整储蓄和流动资金。
        
        Args:
            transaction_id: 收入记录 ID
            update_data: 要更新的字段（如 amount, savings_amount, liquid_amount 等）
        
        Returns:
            dict: 更新后的收入记录，如果未找到则返回空字典
        """
        data = self._read_data()
        
        # 找到要更新的记录
        income_to_update = None
        record_index = None
        for i, record in enumerate(data["income_records"]):
            if record["transaction_id"] == transaction_id:
                income_to_update = record.copy()
                record_index = i
                break
        
        if not income_to_update:
            return {}
        
        account_manager = AccountManager(self.user_id)
        
        # 计算旧分配金额
        old_savings = float(income_to_update.get("savings_amount", 0.0))
        old_liquid = float(income_to_update.get("liquid_amount", 0.0))
        old_amount = float(income_to_update.get("amount", 0.0))
        
        # 计算新分配金额（如果 update_data 中提供了的话）
        new_amount = float(update_data.get("amount", old_amount))
        new_savings = float(update_data.get("savings_amount", old_savings))
        new_liquid = float(update_data.get("liquid_amount", old_liquid))
        
        # 如果有新的分配比例，重新计算
        if "savings_ratio" in update_data or "liquid_ratio" in update_data:
            savings_ratio = float(update_data.get("savings_ratio", 0.1))
            liquid_ratio = float(update_data.get("liquid_ratio", 0.9))
            new_savings = round(new_amount * savings_ratio, 2)
            new_liquid = round(new_amount * liquid_ratio, 2)
        
        # 回滚旧分配：从储蓄扣除old_savings，从流动资金扣除old_liquid
        if old_savings > 0:
            account_manager.adjust_balance("savings", -old_savings)
        if old_liquid > 0:
            account_manager.adjust_balance("liquid", -old_liquid)
        
        # 应用新分配：向储蓄增加new_savings，向流动资金增加new_liquid
        if new_savings > 0:
            account_manager.adjust_balance("savings", new_savings)
        if new_liquid > 0:
            account_manager.adjust_balance("liquid", new_liquid)
        
        # 更新记录
        data["income_records"][record_index]["amount"] = new_amount
        data["income_records"][record_index]["savings_amount"] = new_savings
        data["income_records"][record_index]["liquid_amount"] = new_liquid
        data["income_records"][record_index]["updated_at"] = datetime.now().isoformat()
        
        # 更新其他可选字段
        if "category" in update_data:
            data["income_records"][record_index]["category"] = update_data["category"]
        if "subcategory" in update_data:
            data["income_records"][record_index]["subcategory"] = update_data["subcategory"]
        if "description" in update_data:
            data["income_records"][record_index]["description"] = update_data["description"]
        if "date" in update_data:
            data["income_records"][record_index]["date"] = update_data["date"]
        
        self._write_data(data)
        
        return data["income_records"][record_index]


if __name__ == "__main__":
    # 本地测试
    manager = IncomeManager("test_user")
    
    # 测试添加收入记录
    test_income = {
        "category": "工资",
        "subcategory": "月薪",
        "amount": 5000.0,
        "description": "3月份工资",
        "date": "2026-03-28",
        "savings_amount": 500.0,
        "liquid_amount": 4500.0,
    }
    
    result = manager.add_income(test_income)
    print(f"添加收入记录成功: {result['transaction_id']}")
    
    # 测试获取收入统计
    summary = manager.get_income_summary()
    print(f"收入统计: {summary}")
