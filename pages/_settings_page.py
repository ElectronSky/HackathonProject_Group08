# -*- coding: utf-8 -*-
"""
个性化设置页面
用于查看和修改用户画像设置

入口：app.py 侧边栏 -> "⚙️ 个性化设置"
"""

import sys
import os
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.user_profile_manager import UserProfileManager


def _render_profile_initialization_questionnaire():
    """
    渲染用户画像初始化问卷（在设置页面内展开）。
    用户重新填写时调用此函数。
    """
    st.markdown("### 👋 重新填写初始化问卷")
    st.info("""
    这将重新设置你的个性化信息。完成设置后，我会根据你的新情况提供更贴合的消费建议和分析。
    """)
    
    with st.form("profile_reinit_form"):
        st.markdown("#### 📋 请选择以下选项")
        
        # 维度A：财商知识水平
        st.markdown("**你了解财商知识的程度如何？**")
        knowledge_level = st.radio(
            "财商知识水平",
            [
                "1️⃣ 我是完全的小白，完全不了解任何理财知识",
                "2️⃣ 我听说过一些理财知识，但不知道如何应用到日常生活中",
                "3️⃣ 我有系统性地学习过一些理财知识，但并没有将其运用在生活中",
                "4️⃣ 我有系统性地学习过一些理财知识，并且已经有将其运用在生活的经验"
            ],
            captions=[
                "没关系，我也是从零开始的",
                "知道一点就好，我们慢慢来",
                "很棒，继续保持学习的热情",
                "厉害，可以互相学习"
            ]
        )
        
        # 维度B：消费控制能力
        st.markdown("**你觉得你的消费习惯如何？**")
        spending_control = st.radio(
            "消费控制能力",
            [
                "1️⃣ 感觉自己总是抑制不住消费的冲动，常常会在消费后感到后悔",
                "2️⃣ 我属于月光族，总是无法有效规划自己的消费，勉强达到收支平衡",
                "3️⃣ 我有省钱和计划消费的意识，但实际情况却常常与我的计划背道而驰",
                "4️⃣ 我可以做到有意识地控制消费习惯，并做到每月有一部分储蓄，但希望可以更好"
            ],
            captions=[
                "我懂你冲动消费的快感，一起慢慢改善",
                "月光族也是很有潜力的，关键是要开始",
                "有意识就已经很棒了，我们一起优化",
                "继续保持，争取做得更好"
            ]
        )
        
        # 维度C：经济阶段
        st.markdown("**你目前的经济阶段是？**")
        economic_stage = st.radio(
            "经济阶段",
            [
                "🏠 主要依赖家里（学生阶段）",
                "🚶 半独立（有兼职/生活费混合）",
                "💼 基本独立（已工作）"
            ],
            index=None,
            horizontal=True
        )
        
        # 维度D：当前目标（多选）
        st.markdown("**你最希望通过这个 app 解决什么？（可多选）**")
        col1, col2 = st.columns(2)
        with col1:
            goal_quick_record = st.checkbox("⚡ 快速记账")
            goal_control_impulse = st.checkbox("🧠 控制冲动消费")
        with col2:
            goal_budget = st.checkbox("📊 做预算不超支")
            goal_finance = st.checkbox("📚 学一点真正能用的财商知识")
        
        current_goals = []
        if goal_quick_record:
            current_goals.append("quick_record")
        if goal_control_impulse:
            current_goals.append("control_impulse")
        if goal_budget:
            current_goals.append("budget")
        if goal_finance:
            current_goals.append("finance_knowledge")
        
        # 维度E：AI风格
        st.markdown("**你希望 AI 怎么和你说话？**")
        companion_style = st.radio(
            "AI 陪伴风格",
            [
                "💪 多鼓励我一点",
                "📋 简洁直接",
                "😊 像朋友一样轻松聊天",
                "🏃 像教练一样给我行动建议"
            ],
            horizontal=True
        )
        
        st.markdown("---")
        
        # 可选：自我介绍
        with st.expander("✏️ 更多关于你自己（可选）", expanded=False):
            self_introduction = st.text_area(
                "你可以简单介绍一下自己",
                placeholder="例如：大三学生，宿舍生活，每月家里给2000生活费..."
            )
            
            special_expenses = st.text_area(
                "你有固定的重要消费吗？（每行一条，可选）",
                placeholder="例如：每天需要的药品\n每月固定培训费"
            )
            
            avoid_pushy = st.checkbox("🔕 我希望减少打扰提醒")
        
        st.markdown("---")
        
        # 提交和取消按钮
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("✨ 完成设置", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            # 解析选项
            knowledge_map = {
                "1️⃣ 我是完全的小白": "beginner",
                "2️⃣ 我听说过一些理财知识": "intermediate_known",
                "3️⃣ 我有系统性地学习过一些理财知识": "intermediate_used",
                "4️⃣ 我有系统性地学习过一些理财知识": "advanced"
            }
            finance_knowledge_level = "beginner"
            for k, v in knowledge_map.items():
                if k in knowledge_level:
                    finance_knowledge_level = v
                    break
            
            spending_map = {
                "1️⃣ 感觉自己总是抑制不住": "impulsive",
                "2️⃣ 我属于月光族": "monthly_spender",
                "3️⃣ 我有省钱和计划消费的": "conscious",
                "4️⃣ 我可以做到有意识地控制": "controlled"
            }
            spending_ctrl = "conscious"
            for k, v in spending_map.items():
                if k in spending_control:
                    spending_ctrl = v
                    break
            
            stage_map = {
                "🏠 主要依赖家里": "dependent",
                "🚶 半独立": "semi_independent",
                "💼 基本独立": "independent"
            }
            eco_stage = "dependent"
            for k, v in stage_map.items():
                if k in (economic_stage or ""):
                    eco_stage = v
                    break
            
            style_map = {
                "💪 多鼓励我一点": "encouraging",
                "📋 简洁直接": "direct",
                "😊 像朋友一样轻松聊天": "friendly",
                "🏃 像教练一样给我行动建议": "coach"
            }
            ai_style = "friendly"
            for k, v in style_map.items():
                if k in companion_style:
                    ai_style = v
                    break
            
            # 解析特殊消费
            special_list = []
            if special_expenses:
                special_list = [s.strip() for s in special_expenses.split("\n") if s.strip()]
            
            # 保存画像
            user_id = st.session_state.get("user_id", "guest")
            profile_manager = UserProfileManager(user_id)
            profile_manager.initialize_profile(
                finance_knowledge_level=finance_knowledge_level,
                spending_control=spending_ctrl,
                economic_stage=eco_stage,
                current_goal=current_goals,
                companion_style=ai_style,
                self_introduction=self_introduction or "",
                special_expenses=special_list,
                avoid_pushy=avoid_pushy
            )
            
            # 更新session_state，关闭问卷展开状态
            st.session_state["reinit_profile"] = False
            
            st.success("✅ 设置已更新！我会根据你的新情况提供更贴合的建议！")
            st.rerun()
        
        if cancelled:
            st.session_state["reinit_profile"] = False
            st.rerun()


def show_settings_page():
    """
    个性化设置页面主函数。
    展示当前设置，支持查看和修改。
    """
    
    # 初始化重新填写问卷的状态标记
    if "reinit_profile" not in st.session_state:
        st.session_state["reinit_profile"] = False
    
    # 页面标题
    st.title("⚙️ 个性化设置")
    st.caption("调整这些设置可以让我更好地为你服务")
    st.divider()
    
    # 获取当前用户ID
    user_id = st.session_state.get("user_id", "guest")
    profile_manager = UserProfileManager(user_id)
    profile = profile_manager.get_profile()
    
    # 检查是否正在进行重新填写问卷
    if st.session_state.get("reinit_profile", False):
        _render_profile_initialization_questionnaire()
        return
    
    # 如果没有画像，显示提示
    if not profile:
        st.warning("⚠️ 尚未完成初始化设置")
        st.info("请先完成初始化问卷，让我更好地了解你。")
        if st.button("📋 去填写初始化问卷", type="primary"):
            st.switch_page("pages/_ai_finance_page.py")
        return
    
    # === 查看当前设置 ===
    st.markdown("### 📊 当前设置")
    
    # 创建两列展示
    col1, col2 = st.columns(2)
    
    # 财商知识水平
    with col1:
        level_labels = {
            "beginner": "💭 小白",
            "intermediate_known": "📖 略知",
            "intermediate_used": "📚 学过",
            "advanced": "🎯 有经验"
        }
        current_level = profile.get("finance_knowledge_level", "")
        st.metric("财商知识", level_labels.get(current_level, "未设置"))
        
        # 消费控制能力
        control_labels = {
            "impulsive": "😤 冲动型",
            "monthly_spender": "💸 月光族",
            "conscious": "🤔 有意识",
            "controlled": "👍 有控制力"
        }
        current_control = profile.get("spending_control", "")
        st.metric("消费控制", control_labels.get(current_control, "未设置"))
    
    with col2:
        # 经济阶段
        stage_labels = {
            "dependent": "🏠 依赖家里",
            "semi_independent": "🚶 半独立",
            "independent": "💼 基本独立"
        }
        current_stage = profile.get("economic_stage", "")
        st.metric("经济阶段", stage_labels.get(current_stage, "未设置"))
        
        # AI风格
        style_labels = {
            "encouraging": "💪 鼓励式",
            "direct": "📋 直接式",
            "friendly": "😊 朋友式",
            "coach": "🏃 教练式"
        }
        current_style = profile.get("companion_style", "")
        st.metric("AI风格", style_labels.get(current_style, "未设置"))
    
    # 目标展示
    goal_labels = {
        "quick_record": "快速记账",
        "control_impulse": "控制冲动",
        "budget": "做预算",
        "finance_knowledge": "学财商"
    }
    current_goals = profile.get("current_goal", [])
    if current_goals:
        goal_texts = [goal_labels.get(g, g) for g in current_goals]
        st.markdown(f"**当前目标**：{' | '.join(goal_texts)}")
    
    # 自述信息展示
    st.markdown("---")
    
    if profile.get("self_introduction"):
        with st.expander("📝 自我介绍", expanded=False):
            st.write(profile["self_introduction"])
    
    if profile.get("special_expenses"):
        with st.expander("🏷️ 固定特殊消费", expanded=False):
            for expense in profile["special_expenses"]:
                st.write(f"- {expense}")
    
    if profile.get("avoid_pushy"):
        st.info("🔕 你选择了减少打扰提醒")
    
    # 元数据
    if profile.get("initialized_at"):
        st.caption(f"✨ 初始化时间：{profile.get('initialized_at', '')[:10]}")
    if profile.get("last_updated"):
        st.caption(f"🕐 最后更新：{profile.get('last_updated', '')[:10]}")
    
    st.markdown("---")
    
    # === 重新填写问卷 ===
    st.markdown("### 🔄 重新填写问卷")
    st.caption("如果想重新设置所有选项，可以重新填写问卷")
    
    if st.button("📋 重新填写初始化问卷", use_container_width=True):
        # 设置标记，在当前页面展开问卷
        st.session_state["reinit_profile"] = True
        st.rerun()
    
    st.markdown("---")
    
    # === 修改设置 ===
    st.markdown("### ✏️ 修改设置")
    st.caption("快速修改部分设置，无需重新填写全部问卷")
    
    if st.button("修改我的设置", use_container_width=True):
        st.session_state["editing_profile"] = True
    
    # 渲染编辑表单（在session_state控制下）
    if st.session_state.get("editing_profile", False):
        _render_profile_edit_form(profile_manager, profile)


def _render_profile_edit_form(profile_manager: UserProfileManager, current_profile: dict):
    """
    渲染编辑表单
    
    Args:
        profile_manager: 画像管理器实例
        current_profile: 当前画像字典
    """
    
    with st.form("profile_edit_form"):
        st.markdown("#### 修改个人信息")
        
        # === 财商知识水平 ===
        knowledge_options = {
            "beginner": "1️⃣ 小白",
            "intermediate_known": "2️⃣ 略知",
            "intermediate_used": "3️⃣ 学过",
            "advanced": "4️⃣ 有经验"
        }
        current_level = current_profile.get("finance_knowledge_level", "beginner")
        try:
            level_index = list(knowledge_options.keys()).index(current_level)
        except ValueError:
            level_index = 0
        knowledge_choice = st.selectbox(
            "财商知识水平",
            list(knowledge_options.keys()),
            index=level_index,
            format_func=lambda x: knowledge_options[x]
        )
        
        # === 消费控制能力 ===
        control_options = {
            "impulsive": "1️⃣ 冲动型",
            "monthly_spender": "2️⃣ 月光族",
            "conscious": "3️⃣ 有意识",
            "controlled": "4️⃣ 有控制力"
        }
        current_control = current_profile.get("spending_control", "conscious")
        try:
            control_index = list(control_options.keys()).index(current_control)
        except ValueError:
            control_index = 2
        control_choice = st.selectbox(
            "消费控制能力",
            list(control_options.keys()),
            index=control_index,
            format_func=lambda x: control_options[x]
        )
        
        # === 经济阶段 ===
        stage_options = {
            "dependent": "🏠 主要依赖家里",
            "semi_independent": "🚶 半独立",
            "independent": "💼 基本独立"
        }
        current_stage = current_profile.get("economic_stage", "dependent")
        try:
            stage_index = list(stage_options.keys()).index(current_stage)
        except ValueError:
            stage_index = 0
        stage_choice = st.selectbox(
            "经济阶段",
            list(stage_options.keys()),
            index=stage_index,
            format_func=lambda x: stage_options[x]
        )
        
        # === AI陪伴风格 ===
        style_options = {
            "encouraging": "💪 多鼓励我一点",
            "direct": "📋 简洁直接",
            "friendly": "😊 像朋友聊天",
            "coach": "🏃 像教练给建议"
        }
        current_style = current_profile.get("companion_style", "friendly")
        try:
            style_index = list(style_options.keys()).index(current_style)
        except ValueError:
            style_index = 3
        style_choice = st.selectbox(
            "AI风格",
            list(style_options.keys()),
            index=style_index,
            format_func=lambda x: style_options[x]
        )
        
        st.markdown("---")
        
        # === 用户自述编辑 ===
        st.markdown("##### ✏️ 自述信息")
        
        intro = st.text_area(
            "自我介绍",
            value=current_profile.get("self_introduction", ""),
            placeholder="例如：大三学生，宿舍生活，每月家里给2000生活费..."
        )
        
        special = st.text_area(
            "固定特殊消费（每行一条）",
            value="\n".join(current_profile.get("special_expenses", [])),
            placeholder="每天需要的药品...\n每月固定培训费..."
        )
        
        avoid_pushy = st.checkbox(
            "减少打扰提醒",
            value=current_profile.get("avoid_pushy", False)
        )
        
        st.markdown("---")
        
        # 提交和取消按钮
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if submitted:
            # 解析special_expenses为列表
            special_expenses = [s.strip() for s in special.split("\n") if s.strip()]
            
            # 更新画像
            profile_manager.update_profile({
                "finance_knowledge_level": knowledge_choice,
                "spending_control": control_choice,
                "economic_stage": stage_choice,
                "companion_style": style_choice,
                "self_introduction": intro,
                "special_expenses": special_expenses,
                "avoid_pushy": avoid_pushy
            })
            
            st.success("✅ 修改已保存！")
            st.session_state["editing_profile"] = False
            st.rerun()
        
        if cancelled:
            st.session_state["editing_profile"] = False
            st.rerun()
