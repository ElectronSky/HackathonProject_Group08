"""
优惠券库读取器。
负责从本地 JSON 文件读取优惠券数据，提供优惠券查询接口。
"""

import json
import os
from typing import List, Optional, Dict

try:
    from .path_tools import get_abs_path
except ImportError:
    from importlib import import_module
    get_abs_path = import_module("utils.path_tools").get_abs_path


class CouponRepository:
    """
    优惠券库读取器。
    
    职责：
    - 从本地 JSON 文件读取优惠券数据
    - 提供优惠券查询接口
    - 返回优惠券完整信息
    """
    
    def __init__(self, catalog_file_path: str = None):
        """
        初始化优惠券库读取器。
        
        Args:
            catalog_file_path: 优惠券库文件路径，None 则使用默认路径
        """
        if catalog_file_path is None:
            catalog_file_path = get_abs_path("data/rewards/rewards_catalog.json")
        self.catalog_file = catalog_file_path
        self._catalog_data = None
    
    def _load_catalog(self) -> dict:
        """
        加载优惠券库数据。
        
        Returns:
            dict: 优惠券库数据
        """
        if self._catalog_data is None:
            if not os.path.exists(self.catalog_file):
                return {"catalog_name": "", "version": "", "rewards": []}
            
            with open(self.catalog_file, 'r', encoding='utf-8') as f:
                self._catalog_data = json.load(f)
        
        return self._catalog_data
    
    def load_all_coupons(self) -> List[dict]:
        """
        加载所有优惠券。
        
        Returns:
            List[dict]: 所有优惠券列表
        """
        catalog = self._load_catalog()
        return catalog.get("rewards", [])
    
    def get_coupon_by_id(self, coupon_id: str) -> Optional[dict]:
        """
        根据优惠券 ID 获取优惠券详情。
        
        Args:
            coupon_id: 优惠券 ID
        
        Returns:
            Optional[dict]: 优惠券详情，未找到返回 None
        """
        coupons = self.load_all_coupons()
        for coupon in coupons:
            if coupon.get("coupon_id") == coupon_id:
                return coupon
        return None
    
    def get_coupons_by_tags(self, tags: List[str]) -> List[dict]:
        """
        根据标签获取优惠券。
        
        Args:
            tags: 标签列表
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        matching = []
        
        for coupon in coupons:
            coupon_tags = coupon.get("tags", [])
            # 检查是否有任何标签匹配
            if any(tag in coupon_tags for tag in tags):
                matching.append(coupon)
        
        return matching
    
    def get_coupons_by_type(self, coupon_type: str) -> List[dict]:
        """
        根据优惠券类型获取优惠券。
        
        Args:
            coupon_type: 优惠券类型
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        return [c for c in coupons if c.get("coupon_type") == coupon_type]
    
    def get_coupons_by_budget_related(self, budget_related: bool = True) -> List[dict]:
        """
        获取与预算相关的优惠券。
        
        Args:
            budget_related: 是否与预算相关
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        matching = []
        
        for coupon in coupons:
            target_match = coupon.get("target_match", {})
            if target_match.get("budget_related", False) == budget_related:
                matching.append(coupon)
        
        return matching
    
    def get_coupons_by_problem_signal(self, problem_signal: str) -> List[dict]:
        """
        根据问题信号获取优惠券。
        
        Args:
            problem_signal: 问题信号关键词
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        matching = []
        
        for coupon in coupons:
            target_match = coupon.get("target_match", {})
            problem_signals = target_match.get("problem_signals", [])
            if problem_signal in problem_signals:
                matching.append(coupon)
        
        return matching
    
    def get_coupons_by_category(self, category: str) -> List[dict]:
        """
        根据消费类别获取优惠券。
        
        Args:
            category: 消费类别
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        matching = []
        
        for coupon in coupons:
            target_match = coupon.get("target_match", {})
            categories = target_match.get("focus_categories", [])
            subcategories = target_match.get("focus_subcategories", [])
            
            if category in categories or category in subcategories:
                matching.append(coupon)
        
        return matching
    
    def get_coupons_by_economic_stage(self, economic_stage: str) -> List[dict]:
        """
        根据经济阶段获取优惠券。
        
        Args:
            economic_stage: 经济阶段
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        matching = []
        
        for coupon in coupons:
            target_match = coupon.get("target_match", {})
            stages = target_match.get("economic_stages", [])
            
            if economic_stage in stages:
                matching.append(coupon)
        
        return matching
    
    def search_coupons(
        self,
        keyword: str = None,
        tags: List[str] = None,
        max_points_cost: int = None,
        economic_stage: str = None
    ) -> List[dict]:
        """
        综合搜索优惠券。
        
        Args:
            keyword: 关键词（搜索标题、描述）
            tags: 标签列表
            max_points_cost: 最大积分成本
            economic_stage: 经济阶段
        
        Returns:
            List[dict]: 匹配的优惠券列表
        """
        coupons = self.load_all_coupons()
        results = coupons
        
        # 关键词过滤
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                c for c in results
                if keyword_lower in c.get("title", "").lower()
                or keyword_lower in c.get("description", "").lower()
            ]
        
        # 标签过滤
        if tags:
            results = [
                c for c in results
                if any(tag in c.get("tags", []) for tag in tags)
            ]
        
        # 积分成本过滤
        if max_points_cost is not None:
            results = [
                c for c in results
                if c.get("points_cost", 0) <= max_points_cost
            ]
        
        # 经济阶段过滤
        if economic_stage:
            results = [
                c for c in results
                if economic_stage in c.get("target_match", {}).get("economic_stages", [])
            ]
        
        return results
    
    def get_coupon_count(self) -> int:
        """
        获取优惠券总数。
        
        Returns:
            int: 优惠券总数
        """
        return len(self.load_all_coupons())
    
    def get_catalog_info(self) -> dict:
        """
        获取优惠券库信息。
        
        Returns:
            dict: 包含库名称、版本、优惠券数量等
        """
        catalog = self._load_catalog()
        return {
            "catalog_name": catalog.get("catalog_name", ""),
            "version": catalog.get("version", ""),
            "description": catalog.get("description", ""),
            "total_coupons": len(catalog.get("rewards", [])),
        }


if __name__ == "__main__":
    # 本地测试
    repo = CouponRepository()
    
    # 测试获取库信息
    info = repo.get_catalog_info()
    print(f"优惠券库信息: {info}")
    
    # 测试加载所有优惠券
    all_coupons = repo.load_all_coupons()
    print(f"优惠券总数: {len(all_coupons)}")
    
    # 测试按标签搜索
    drinks = repo.get_coupons_by_tags(["奶茶", "咖啡"])
    print(f"饮品相关优惠券: {len(drinks)} 张")
    
    # 测试按问题信号搜索
    impulse = repo.get_coupons_by_problem_signal("高频小额支出")
    print(f"高频小额相关优惠券: {len(impulse)} 张")
