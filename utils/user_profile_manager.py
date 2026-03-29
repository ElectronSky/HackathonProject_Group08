# -*- coding: utf-8 -*-
"""
用户画像管理器
负责用户画像的创建、读取、更新、删除

核心功能：
1. 用户画像初始化（首次使用时填写问卷）
2. 用户画像读取和更新
3. 根据画像提供个性化上下文（用于prompt注入）
4. 卡片推荐数量限制计算
"""

import json
import os
from typing import Optional, List


class UserProfileManager:
    """用户画像管理器"""
    
    def __init__(self, user_id: str):
        """
        初始化画像管理器
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        # 数据存储目录
        self.data_dir = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "users",
            user_id
        )
        # 画像文件路径
        self.file_path = os.path.join(
            self.data_dir, 
            "profile.json"
        )
    
    # ==================== 基础CRUD方法 ====================
    
    def get_profile(self) -> Optional[dict]:
        """
        获取用户画像，若不存在返回None
        
        Returns:
            用户画像字典，若不存在返回None
        """
        if not os.path.exists(self.file_path):
            return None
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def save_profile(self, profile: dict) -> None:
        """
        保存用户画像到文件
        
        Args:
            profile: 用户画像字典
        """
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 写入文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    
    def delete_profile(self) -> bool:
        """
        删除用户画像文件
        
        Returns:
            是否删除成功
        """
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            return True
        return False
    
    def is_initialized(self) -> bool:
        """
        检查用户是否已完成初始化
        
        Returns:
            是否已初始化
        """
        profile = self.get_profile()
        return profile is not None and profile.get("profile_version") is not None
    
    # ==================== 初始化方法 ====================
    
    def initialize_profile(
        self,
        finance_knowledge_level: str,
        spending_control: str,
        economic_stage: str,
        current_goal: List[str],
        companion_style: str,
        self_introduction: str = "",
        special_expenses: List[str] = None,
        avoid_pushy: bool = False
    ) -> dict:
        """
        初始化用户画像（首次设置）
        
        Args:
            finance_knowledge_level: 财商知识水平 (beginner/intermediate_known/intermediate_used/advanced)
            spending_control: 消费控制能力 (impulsive/monthly_spender/conscious/controlled)
            economic_stage: 经济阶段 (dependent/semi_independent/independent)
            current_goal: 当前目标列表
            companion_style: AI陪伴风格 (encouraging/direct/friendly/coach)
            self_introduction: 用户自我介绍
            special_expenses: 固定特殊消费列表
            avoid_pushy: 是否减少打扰
        
        Returns:
            创建的画像字典
        """
        from datetime import datetime
        
        profile = {
            "user_id": self.user_id,
            "finance_knowledge_level": finance_knowledge_level,
            "spending_control": spending_control,
            "economic_stage": economic_stage,
            "current_goal": current_goal,
            "companion_style": companion_style,
            "self_introduction": self_introduction,
            "special_expenses": special_expenses or [],
            "avoid_pushy": avoid_pushy,
            "initialized_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "profile_version": 1
        }
        
        self.save_profile(profile)
        return profile
    
    # ==================== 更新方法 ====================
    
    def update_profile(self, updates: dict) -> dict:
        """
        更新用户画像的指定字段
        
        Args:
            updates: 要更新的字段字典
        
        Returns:
            更新后的画像字典
        """
        from datetime import datetime
        
        profile = self.get_profile() or {}
        profile.update(updates)
        profile["last_updated"] = datetime.now().isoformat()
        
        self.save_profile(profile)
        return profile
    
    def update_self_introduction(self, introduction: str) -> None:
        """
        更新用户自我介绍
        
        Args:
            introduction: 新的自我介绍文本
        """
        self.update_profile({"self_introduction": introduction})
    
    def update_special_expenses(self, expenses: List[str]) -> None:
        """
        更新用户固定特殊消费列表
        
        Args:
            expenses: 新的特殊消费列表
        """
        self.update_profile({"special_expenses": expenses})
    
    def update_avoid_pushy(self, avoid_pushy: bool) -> None:
        """
        更新打扰偏好设置
        
        Args:
            avoid_pushy: 是否减少打扰
        """
        self.update_profile({"avoid_pushy": avoid_pushy})
    
    # ==================== 获取器方法 ====================
    
    def get_companion_style(self) -> str:
        """
        获取AI陪伴风格
        
        Returns:
            陪伴风格标识符
        """
        profile = self.get_profile()
        return profile.get("companion_style", "friendly") if profile else "friendly"
    
    def get_economic_stage(self) -> str:
        """
        获取经济阶段
        
        Returns:
            经济阶段标识符
        """
        profile = self.get_profile()
        return profile.get("economic_stage", "dependent") if profile else "dependent"
    
    def get_finance_knowledge_level(self) -> str:
        """
        获取财商知识水平
        
        Returns:
            知识水平标识符
        """
        profile = self.get_profile()
        return profile.get("finance_knowledge_level", "beginner") if profile else "beginner"
    
    def get_spending_control(self) -> str:
        """
        获取消费控制能力
        
        Returns:
            消费控制能力标识符
        """
        profile = self.get_profile()
        return profile.get("spending_control", "conscious") if profile else "conscious"
    
    def get_card_recommendation_limit(self) -> int:
        """
        根据用户画像决定推荐卡片数量上限
        
        规则：
        - 新手/冲动型/月光族：只推1张
        - 有意愿学财商 + 有一定控制力：可推2张
        - 其他情况：默认1张
        
        Returns:
            推荐卡片数量上限 (1或2)
        """
        profile = self.get_profile()
        if not profile:
            return 1
        
        spending_control = profile.get("spending_control", "conscious")
        current_goal = profile.get("current_goal", [])
        
        # 新手/冲动型/月光族：只推1张
        if spending_control in ["impulsive", "monthly_spender"]:
            return 1
        
        # 有意愿学财商 + 有一定控制力：可推2张
        if ("finance_knowledge" in current_goal and 
            spending_control == "conscious"):
            return 2
        
        return 1
    
    def get_persona_context(self) -> dict:
        """
        根据用户画像构建建议上下文
        
        用于注入到evidence pack或prompt中，控制建议的现实性
        
        Args:
            profile: 用户画像字典
        
        Returns:
            建议上下文字典，包含advice_focus、avoid_topics、example_categories
        """
        economic_stage = self.get_economic_stage()
        
        if economic_stage == "dependent":
            return {
                "advice_focus": ["餐饮控制", "娱乐消费", "小额高频支出", "人情往来"],
                "avoid_topics": ["储蓄比例", "投资理财", "月结余规划", "保险配置"],
                "example_categories": ["食堂", "外卖", "奶茶", "游戏", "服饰", "社交"]
            }
        elif economic_stage == "semi_independent":
            return {
                "advice_focus": ["餐饮", "交通", "兼职收入分配", "储蓄起步", "预算分配", "收支平衡"],
                "avoid_topics": ["大额投资", "复杂保险配置"],
                "example_categories": ["餐饮", "交通", "社交", "自我提升", "兼职", "租房"]
            }
        else:  # independent
            return {
                "advice_focus": ["储蓄比例", "收支平衡", "预算执行", "消费复盘", "投资入门", "保险基础"],
                "avoid_topics": [],
                "example_categories": ["住房", "交通", "餐饮", "投资", "保险", "教育"]
            }
    
    def build_user_context_block(self) -> str:
        """
        构建用户特殊背景信息区块
        
        用于注入到系统提示词的固定位置
        
        Returns:
            格式化的用户上下文字符串
        """
        profile = self.get_profile()
        if not profile:
            return ""
        
        context_parts = []
        
        # 1. 自述介绍
        if profile.get("self_introduction"):
            context_parts.append(
                f"【用户自我介绍】\n{profile['self_introduction']}"
            )
        
        # 2. 固定特殊消费（最重要，防止误判）
        if profile.get("special_expenses"):
            special_text = "\n".join([f"- {expense}" for expense in profile["special_expenses"]])
            context_parts.append(
                f"【用户的固定特殊消费】\n"
                f"以下消费是用户的固定必要支出，在分析时请排除在异常支出判断之外：\n{special_text}"
            )
        
        # 3. 特殊偏好
        if profile.get("avoid_pushy"):
            context_parts.append(
                "【用户偏好】用户不希望被频繁打扰提醒，请减少不必要的催促性语言。"
            )
        
        # 4. 经济阶段
        economic_stage = profile.get("economic_stage", "dependent")
        stage_label = {
            "dependent": "依赖家里（学生阶段）",
            "semi_independent": "半独立（兼职+生活费混合）",
            "independent": "基本独立（已工作）"
        }
        context_parts.append(
            f"【用户经济阶段】{stage_label.get(economic_stage, '未设置')}"
        )
        
        # 5. 财商知识水平（用于调整术语使用）
        knowledge_level = profile.get("finance_knowledge_level", "beginner")
        level_label = {
            "beginner": "小白（完全不了解理财知识）",
            "intermediate_known": "略知（听说过但不会用）",
            "intermediate_used": "学过（但没应用过）",
            "advanced": "有经验（已在生活中实践）"
        }
        context_parts.append(
            f"【用户财商知识水平】{level_label.get(knowledge_level, '未设置')}"
        )
        
        # 拼接成固定区块
        if context_parts:
            return "\n\n" + "\n\n".join(context_parts) + "\n"
        
        return ""
    
    def build_personality_rules(self) -> str:
        """
        构建个性化语气规则注入文本
        
        Returns:
            语气规则字符串
        """
        profile = self.get_profile()
        if not profile:
            return ""
        
        style = profile.get("companion_style", "friendly")
        knowledge = profile.get("finance_knowledge_level", "beginner")
        
        # 语气规则
        style_rules = {
            "encouraging": "【语气要求】多用鼓励语言，肯定用户的努力成果。即使指出问题也要先肯定做得好的地方。使用'你做得不错'、'继续保持'等正向反馈。少用'但是'、'不过'、'不要'等转折词。",
            "direct": "【语气要求】简洁直接，给出明确结论。不废话，直接告诉用户该怎么做。开头直接说结论，再简短解释原因。避免过多的安慰性语言。",
            "friendly": "【语气要求】轻松友好，像朋友聊天。可以适当用emoji（😊👍🎉等），语气亲切但保持专业。可以用'我懂你'、'哈哈'等口语化表达。",
            "coach": "【语气要求】给出清晰行动建议和执行计划。像教练一样有步骤地引导用户。使用'第一步'、'接下来'、'然后'等引导词。给出可量化的目标和检查点。"
        }
        
        # 知识深度规则
        knowledge_rules = {
            "beginner": "【知识深度】使用通俗易懂的语言，多用比喻，解释每个专业术语的含义。举例要贴近日常生活（如食堂就餐、奶茶消费）。避免直接使用英文缩写（如ROI、NAPR等）。",
            "intermediate_known": "【知识深度】适度使用专业术语，稍作解释。可以简要说明原理，举例可以稍微复杂一些。",
            "intermediate_used": "【知识深度】适度使用专业术语，稍作解释。可以讲解原理和实际应用案例。",
            "advanced": "【知识深度】可直接使用专业术语，用户能理解更深层原理。可以讲解更深层的经济学/心理学原理，举例可以包含实际案例分析。"
        }
        
        return "\n\n" + style_rules.get(style, style_rules["friendly"]) + "\n\n" + knowledge_rules.get(knowledge, knowledge_rules["beginner"]) + "\n"
