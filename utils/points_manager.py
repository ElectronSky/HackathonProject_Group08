"""
积分账户管理器。
负责管理用户的积分余额、积分变动历史、优惠券兑换记录。
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict

try:
    from .path_tools import get_abs_path
except ImportError:
    from importlib import import_module
    get_abs_path = import_module("utils.path_tools").get_abs_path


class PointsManager:
    """
    积分账户管理器。
    
    职责：
    - 管理用户积分余额
    - 记录积分变动历史
    - 处理积分扣除（兑换）
    - 查询积分状态
    """
    
    # 积分获取规则
    POINTS_RULES = {
        "record_expense": 5,          # 每记账一笔
        "card_completed": 100,        # 知识卡片完成
        "finance_analysis": 20,        # 财商分析完成
        "budget_created": 15,          # 首次设置预算
        "daily_checkin": 10,          # 每日打卡（连续7天）
        "savings_goal_reached": 50,   # 达到储蓄目标
    }
    
    def __init__(self, user_id: str):
        """
        初始化积分管理器。
        
        Args:
            user_id: 用户唯一标识符
        """
        self.user_id = user_id
        self.points_dir = get_abs_path("data/points")
        self.points_file = os.path.join(self.points_dir, f"{user_id}_points.json")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保积分文件存在，不存在则创建初始结构"""
        if not os.path.exists(self.points_dir):
            os.makedirs(self.points_dir)
        
        if not os.path.exists(self.points_file):
            initial_data = {
                "user_id": self.user_id,
                "total_points": 0,
                "lifetime_points": 0,
                "point_history": [],
                "exchanged_coupons": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._write_data(initial_data)
    
    def _read_data(self) -> dict:
        """
        读取积分数据文件。
        
        Returns:
            dict: 积分数据
        """
        with open(self.points_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def _write_data(self, data: dict) -> None:
        """
        写入积分数据文件。
        
        Args:
            data: 积分数据字典
        """
        data["updated_at"] = datetime.now().isoformat()
        with open(self.points_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_balance(self) -> int:
        """
        获取当前积分余额。
        
        Returns:
            int: 当前积分余额
        """
        data = self._read_data()
        return data.get("total_points", 0)
    
    def get_lifetime_points(self) -> int:
        """
        获取累计获得积分。
        
        Returns:
            int: 累计获得积分
        """
        data = self._read_data()
        return data.get("lifetime_points", 0)
    
    def get_history(self, limit: int = 20) -> List[dict]:
        """
        获取积分变动历史。
        
        Args:
            limit: 返回记录数量限制（默认 20）
        
        Returns:
            List[dict]: 积分变动历史列表
        """
        data = self._read_data()
        history = data.get("point_history", [])
        # 返回最近的记录（倒序）
        return list(reversed(history))[:limit]
    
    def add_points(self, action: str, description: str = "") -> dict:
        """
        添加积分。
        
        Args:
            action: 积分获取行为（对应 POINTS_RULES 中的键）
            description: 积分变动描述
        
        Returns:
            dict: 包含操作结果的字典
        """
        # 获取积分数量
        points = self.POINTS_RULES.get(action, 0)
        if points <= 0:
            return {
                "success": False,
                "error": f"未知的积分行为: {action}",
                "points_earned": 0,
                "balance_after": self.get_balance()
            }
        
        data = self._read_data()
        now = datetime.now()
        
        # 更新余额
        old_balance = data.get("total_points", 0)
        new_balance = old_balance + points
        
        data["total_points"] = new_balance
        data["lifetime_points"] = data.get("lifetime_points", 0) + points
        
        # 记录历史
        history_entry = {
            "id": f"pt_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "action": action,
            "points": points,
            "balance_after": new_balance,
            "timestamp": now.isoformat(),
            "description": description or self._get_action_description(action),
        }
        
        data.setdefault("point_history", []).insert(0, history_entry)
        
        # 只保留最近 100 条历史
        if len(data["point_history"]) > 100:
            data["point_history"] = data["point_history"][:100]
        
        self._write_data(data)
        
        return {
            "success": True,
            "action": action,
            "points_earned": points,
            "balance_after": new_balance,
            "lifetime_points": data["lifetime_points"],
        }
    
    def deduct_points(self, points: int, reason: str = "") -> dict:
        """
        扣除积分。
        
        Args:
            points: 要扣除的积分数量
            reason: 扣除原因
        
        Returns:
            dict: 包含操作结果的字典
        
        Raises:
            ValueError: 积分不足时抛出异常
        """
        if points <= 0:
            return {
                "success": False,
                "error": "扣除积分必须大于 0",
                "points_deducted": 0,
                "balance_after": self.get_balance()
            }
        
        data = self._read_data()
        now = datetime.now()
        
        old_balance = data.get("total_points", 0)
        
        # 检查积分是否足够
        if old_balance < points:
            return {
                "success": False,
                "error": f"积分不足。当前余额: {old_balance}，需要: {points}",
                "points_deducted": 0,
                "balance_after": old_balance
            }
        
        new_balance = old_balance - points
        data["total_points"] = new_balance
        
        # 记录历史（扣减用负数）
        history_entry = {
            "id": f"pt_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "action": "exchange",
            "points": -points,
            "balance_after": new_balance,
            "timestamp": now.isoformat(),
            "description": reason or "积分兑换",
        }
        
        data.setdefault("point_history", []).insert(0, history_entry)
        self._write_data(data)
        
        return {
            "success": True,
            "points_deducted": points,
            "balance_after": new_balance,
        }
    
    def add_exchanged_coupon(self, coupon_id: str, coupon_title: str, points_spent: int) -> dict:
        """
        添加已兑换的优惠券记录。
        
        Args:
            coupon_id: 优惠券 ID
            coupon_title: 优惠券标题
            points_spent: 消耗的积分
        
        Returns:
            dict: 包含操作结果的字典
        """
        data = self._read_data()
        now = datetime.now()
        
        exchanged_entry = {
            "exchange_id": f"exc_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "coupon_id": coupon_id,
            "coupon_title": coupon_title,
            "points_spent": points_spent,
            "exchanged_at": now.isoformat(),
            "status": "available",
            "code": self._generate_coupon_code(),
        }
        
        data.setdefault("exchanged_coupons", []).insert(0, exchanged_entry)
        self._write_data(data)
        
        return {
            "success": True,
            "exchange_id": exchanged_entry["exchange_id"],
            "coupon_code": exchanged_entry["code"],
        }
    
    def get_exchanged_coupons(self, status: str = None) -> List[dict]:
        """
        获取已兑换的优惠券列表。
        
        Args:
            status: 筛选状态（available/used/expired），None 表示全部
        
        Returns:
            List[dict]: 已兑换优惠券列表
        """
        data = self._read_data()
        coupons = data.get("exchanged_coupons", [])
        
        if status:
            coupons = [c for c in coupons if c.get("status") == status]
        
        return coupons
    
    def use_coupon(self, exchange_id: str) -> dict:
        """
        使用优惠券（标记为已使用）。
        
        Args:
            exchange_id: 兑换记录 ID
        
        Returns:
            dict: 操作结果
        """
        data = self._read_data()
        
        for coupon in data.get("exchanged_coupons", []):
            if coupon.get("exchange_id") == exchange_id:
                coupon["status"] = "used"
                coupon["used_at"] = datetime.now().isoformat()
                self._write_data(data)
                return {
                    "success": True,
                    "coupon_title": coupon.get("coupon_title"),
                    "coupon_code": coupon.get("code"),
                }
        
        return {
            "success": False,
            "error": "未找到该优惠券"
        }
    
    def get_summary(self) -> dict:
        """
        获取积分账户摘要。
        
        Returns:
            dict: 包含积分余额、累计积分、兑换记录统计
        """
        data = self._read_data()
        
        exchanged_coupons = data.get("exchanged_coupons", [])
        
        return {
            "total_points": data.get("total_points", 0),
            "lifetime_points": data.get("lifetime_points", 0),
            "exchanged_count": len(exchanged_coupons),
            "available_count": len([c for c in exchanged_coupons if c.get("status") == "available"]),
            "used_count": len([c for c in exchanged_coupons if c.get("status") == "used"]),
        }
    
    def _get_action_description(self, action: str) -> str:
        """
        获取行为的描述文本。
        
        Args:
            action: 行为标识
        
        Returns:
            str: 行为描述
        """
        descriptions = {
            "record_expense": "记账奖励",
            "card_completed": "知识卡片完成",
            "finance_analysis": "财商分析完成",
            "budget_created": "设置预算奖励",
            "daily_checkin": "每日打卡",
            "savings_goal_reached": "达成储蓄目标",
        }
        return descriptions.get(action, action)
    
    def _generate_coupon_code(self) -> str:
        """
        生成优惠券码。
        
        Returns:
            str: 优惠券码
        """
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        return "COUPON_" + ''.join(random.choices(chars, k=8))


if __name__ == "__main__":
    # 本地测试
    manager = PointsManager("test_user")
    
    # 测试获取摘要
    summary = manager.get_summary()
    print(f"积分摘要: {summary}")
    
    # 测试添加积分
    result = manager.add_points("record_expense", "测试记账")
    print(f"添加积分结果: {result}")
    
    # 再次获取摘要
    summary = manager.get_summary()
    print(f"积分摘要: {summary}")
    
    # 测试积分历史
    history = manager.get_history()
    print(f"积分历史: {history}")
