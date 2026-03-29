"""
储蓄账户和流动资金管理器
负责管理储蓄账户和流动资金的余额、变动历史
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict

try:
    from .path_tools import get_abs_path
except ImportError:
    from importlib import import_module
    get_abs_path = import_module("utils.path_tools").get_abs_path


class AccountManager:
    """
    储蓄账户和流动资金管理器。
    
    职责：
    - 管理储蓄账户和流动资金的余额
    - 记录账户变动历史
    - 支持收入分配
    - 支持手动调整余额
    """
    
    def __init__(self, user_id: str):
        """
        初始化账户管理器。
        
        Args:
            user_id: 用户唯一标识符
        """
        self.user_id = user_id
        self.accounts_file = get_abs_path(f"data/users/{user_id}/accounts.json")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保账户文件存在，不存在则创建初始结构"""
        accounts_dir = os.path.dirname(self.accounts_file)
        if not os.path.exists(accounts_dir):
            os.makedirs(accounts_dir)
        
        if not os.path.exists(self.accounts_file):
            initial_data = {
                "user_id": self.user_id,
                "accounts": {
                    "savings": {
                        "balance": 0.0,
                        "last_updated": datetime.now().isoformat(),
                        "history": [],
                    },
                    "liquid": {
                        "balance": 0.0,
                        "last_updated": datetime.now().isoformat(),
                        "history": [],
                    },
                },
                "auto_allocate_rules": {
                    "enabled": True,
                    "default_savings_ratio": 0.1,
                    "default_liquid_ratio": 0.9,
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._write_data(initial_data)
    
    def _read_data(self) -> dict:
        """
        读取账户数据文件。
        
        Returns:
            dict: 账户数据
        """
        with open(self.accounts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def _write_data(self, data: dict) -> None:
        """
        写入账户数据文件。
        
        Args:
            data: 账户数据字典
        """
        data["updated_at"] = datetime.now().isoformat()
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_balance(self, account_type: str = "savings") -> float:
        """
        获取账户余额。
        
        Args:
            account_type: 账户类型，"savings"（储蓄）或 "liquid"（流动资金）
        
        Returns:
            float: 账户余额
        """
        data = self._read_data()
        accounts = data.get("accounts", {})
        account = accounts.get(account_type, {})
        return float(account.get("balance", 0.0))
    
    def get_total_assets(self) -> float:
        """
        获取总资产（储蓄 + 流动资金）。
        
        Returns:
            float: 总资产
        """
        return self.get_balance("savings") + self.get_balance("liquid")
    
    def get_account_summary(self) -> dict:
        """
        获取账户摘要。
        
        Returns:
            dict: 账户摘要，包含：
                - savings_balance: 储蓄账户余额
                - liquid_balance: 流动资金余额
                - total_assets: 总资产
        """
        return {
            "savings_balance": self.get_balance("savings"),
            "liquid_balance": self.get_balance("liquid"),
            "total_assets": self.get_total_assets(),
        }
    
    def allocate_income(self,
                       total_amount: float,
                       savings_ratio: float = 0.1,
                       liquid_ratio: float = 0.9) -> dict:
        """
        计算收入分配金额。
        
        Args:
            total_amount: 收入总额
            savings_ratio: 存入储蓄的比例（默认 0.1）
            liquid_ratio: 进入流动资金的比例（默认 0.9）
        
        Returns:
            dict: 分配结果，包含：
                - savings_amount: 存入储蓄的金额
                - liquid_amount: 进入流动资金的金额
        """
        savings_amount = round(total_amount * savings_ratio, 2)
        liquid_amount = round(total_amount * liquid_ratio, 2)
        
        return {
            "savings_amount": savings_amount,
            "liquid_amount": liquid_amount,
        }
    
    def record_income_allocation(self,
                                 income_transaction_id: str,
                                 savings_change: float,
                                 liquid_change: float,
                                 note: str = "") -> None:
        """
        记录收入分配到账户。
        
        Args:
            income_transaction_id: 收入记录 ID
            savings_change: 储蓄账户变化金额
            liquid_change: 流动资金变化金额
            note: 备注
        """
        data = self._read_data()
        accounts = data.get("accounts", {})
        now = datetime.now().isoformat()
        
        # 更新储蓄账户
        if savings_change != 0:
            savings_account = accounts.get("savings", {})
            old_balance = float(savings_account.get("balance", 0.0))
            new_balance = old_balance + savings_change
            savings_account["balance"] = round(new_balance, 2)
            savings_account["last_updated"] = now
            
            # 记录历史
            history_entry = {
                "date": now,
                "change": savings_change,
                "balance_after": round(new_balance, 2),
                "source": "income_record",
                "transaction_id": income_transaction_id,
                "note": note or "收入分配",
            }
            savings_account.setdefault("history", []).append(history_entry)
            
            accounts["savings"] = savings_account
        
        # 更新流动资金
        if liquid_change != 0:
            liquid_account = accounts.get("liquid", {})
            old_balance = float(liquid_account.get("balance", 0.0))
            new_balance = old_balance + liquid_change
            liquid_account["balance"] = round(new_balance, 2)
            liquid_account["last_updated"] = now
            
            # 记录历史
            history_entry = {
                "date": now,
                "change": liquid_change,
                "balance_after": round(new_balance, 2),
                "source": "income_record",
                "transaction_id": income_transaction_id,
                "note": note or "收入分配",
            }
            liquid_account.setdefault("history", []).append(history_entry)
            
            accounts["liquid"] = liquid_account
        
        data["accounts"] = accounts
        self._write_data(data)
    
    def adjust_balance(self,
                      account_type: str,
                      change_amount: float,
                      note: str = "") -> dict:
        """
        手动调整账户余额。
        
        重要说明：当调整储蓄账户时，流动资金会自动做反向调整（联动转账）。
        例如：向储蓄账户存入100元，流动资金会自动减少100元。
        
        Args:
            account_type: 账户类型，"savings" 或 "liquid"
            change_amount: 变化金额（正数增加，负数减少）
            note: 调整原因
        
        Returns:
            dict: 调整结果，包含：
                - old_balance: 调整前余额
                - change_amount: 变化金额
                - new_balance: 调整后余额
        
        Note: 允许余额为负数（透支），不会抛出异常。
        """
        if account_type not in ["savings", "liquid"]:
            raise ValueError("account_type 必须是 'savings' 或 'liquid'")
        
        data = self._read_data()
        accounts = data.get("accounts", {})
        now = datetime.now().isoformat()
        
        # 获取调整账户的旧余额
        target_account = accounts.get(account_type, {})
        old_balance = float(target_account.get("balance", 0.0))
        new_balance = old_balance + change_amount
        
        # 注意：允许余额为负数，不做余额检查
        
        # 更新目标账户余额
        target_account["balance"] = round(new_balance, 2)
        target_account["last_updated"] = now
        
        # 记录目标账户历史
        target_history_entry = {
            "date": now,
            "change": change_amount,
            "balance_after": round(new_balance, 2),
            "source": "transfer",
            "note": note or ("存入储蓄账户" if change_amount > 0 else "取出到流动资金"),
        }
        target_account.setdefault("history", []).append(target_history_entry)
        accounts[account_type] = target_account
        
        # 联动调整另一账户（当调整储蓄账户时）
        if account_type == "savings" and change_amount != 0:
            opposite_type = "liquid"
            opposite_change = -change_amount  # 反向变动
            
            opposite_account = accounts.get(opposite_type, {})
            opposite_old_balance = float(opposite_account.get("balance", 0.0))
            opposite_new_balance = opposite_old_balance + opposite_change
            
            # 更新另一账户余额
            opposite_account["balance"] = round(opposite_new_balance, 2)
            opposite_account["last_updated"] = now
            
            # 记录另一账户历史
            opposite_history_entry = {
                "date": now,
                "change": opposite_change,
                "balance_after": round(opposite_new_balance, 2),
                "source": "transfer",
                "note": note or ("流动资金转出" if opposite_change < 0 else "流动资金转入"),
            }
            opposite_account.setdefault("history", []).append(opposite_history_entry)
            accounts[opposite_type] = opposite_account
        
        data["accounts"] = accounts
        self._write_data(data)
        
        return {
            "old_balance": old_balance,
            "change_amount": change_amount,
            "new_balance": round(new_balance, 2),
        }
    
    def get_account_history(self, account_type: str = "savings", limit: int = 20) -> List[dict]:
        """
        获取账户变动历史。
        
        Args:
            account_type: 账户类型
            limit: 返回记录数量限制（默认 20）
        
        Returns:
            List[dict]: 变动历史列表
        """
        data = self._read_data()
        accounts = data.get("accounts", {})
        account = accounts.get(account_type, {})
        history = account.get("history", [])
        
        # 返回最近的记录
        return history[-limit:] if len(history) > limit else history
    
    def get_auto_allocate_rules(self) -> dict:
        """
        获取自动分配规则。
        
        Returns:
            dict: 分配规则，包含：
                - enabled: 是否启用
                - default_savings_ratio: 默认储蓄比例
                - default_liquid_ratio: 默认流动资金比例
        """
        data = self._read_data()
        return data.get("auto_allocate_rules", {
            "enabled": True,
            "default_savings_ratio": 0.1,
            "default_liquid_ratio": 0.9,
        })
    
    def set_auto_allocate_rules(self,
                               enabled: bool = True,
                               savings_ratio: float = 0.1,
                               liquid_ratio: float = 0.9) -> None:
        """
        设置自动分配规则。
        
        Args:
            enabled: 是否启用
            savings_ratio: 默认储蓄比例
            liquid_ratio: 默认流动资金比例
        """
        data = self._read_data()
        data["auto_allocate_rules"] = {
            "enabled": enabled,
            "default_savings_ratio": savings_ratio,
            "default_liquid_ratio": liquid_ratio,
        }
        self._write_data(data)


if __name__ == "__main__":
    # 本地测试
    manager = AccountManager("test_user")
    
    # 测试获取账户摘要
    summary = manager.get_account_summary()
    print(f"账户摘要: {summary}")
    
    # 测试收入分配
    allocation = manager.allocate_income(5000.0, 0.1, 0.9)
    print(f"收入分配: {allocation}")
    
    # 测试记录收入分配
    manager.record_income_allocation(
        income_transaction_id="income_test_001",
        savings_change=500.0,
        liquid_change=4500.0,
        note="工资分配"
    )
    print(f"记录收入分配后的摘要: {manager.get_account_summary()}")
    
    # 测试手动调整余额
    result = manager.adjust_balance(
        account_type="savings",
        change_amount=-200.0,
        note="取出200元"
    )
    print(f"手动调整结果: {result}")
