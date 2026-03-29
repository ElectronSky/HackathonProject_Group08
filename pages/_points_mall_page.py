"""
积分商城页面。
展示用户积分余额、优惠券推荐、我的优惠券、积分记录等功能。
采用 Agent 驱动推荐，支持可视化分析过程展示。
"""

import time
import streamlit as st
from datetime import datetime
from utils.points_manager import PointsManager
from utils.coupon_repository import CouponRepository
from utils.user_profile_manager import UserProfileManager
from utils.evidence_pack_builder import FinanceEvidencePackBuilder


def show_points_mall_page():
    """
    积分商城主页面。
    
    页面结构：
    1. 积分概览区（余额、累计、兑换统计）
    2. AI 智能推荐区（Agent 驱动优惠券推荐）
    3. 我的优惠券区（已兑换优惠券）
    4. 积分记录区（积分变动历史）
    """
    # 页面标题
    st.header("🎁 积分商城")
    st.caption("用积分兑换优惠券，省钱从我做起")
    
    # 获取当前用户
    user_id = st.session_state.get("user_id", "guest")
    
    # 初始化管理器
    points_manager = PointsManager(user_id)
    coupon_repo = CouponRepository()
    profile_manager = UserProfileManager(user_id)
    
    # 获取积分摘要
    points_summary = points_manager.get_summary()
    
    # ==================== 积分概览区 ====================
    _render_points_overview(points_summary)
    
    st.divider()
    
    # ==================== AI 智能推荐区 ====================
    st.subheader("🔍 AI 智能推荐优惠券")
    
    # 初始化 session state
    if "coupon_recommendations" not in st.session_state:
        st.session_state["coupon_recommendations"] = []
    if "show_recommendation_result" not in st.session_state:
        st.session_state["show_recommendation_result"] = False
    if "recommendation_in_progress" not in st.session_state:
        st.session_state["recommendation_in_progress"] = False
    
    # AI 推荐按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🤖 AI 推荐优惠券", type="primary", use_container_width=True):
            st.session_state["recommendation_in_progress"] = True
            st.session_state["show_recommendation_result"] = False
            st.session_state["coupon_recommendations"] = []
    
    with col2:
        st.caption("基于你的消费习惯，AI 为你智能匹配最合适的优惠券")
    
    # 推荐结果区域
    if st.session_state["recommendation_in_progress"]:
        _run_coupon_recommendation_flow(
            user_id=user_id,
            points_manager=points_manager,
            coupon_repo=coupon_repo,
            profile_manager=profile_manager
        )
    
    # 展示推荐结果
    if st.session_state["show_recommendation_result"] and st.session_state["coupon_recommendations"]:
        _render_recommendations(
            st.session_state["coupon_recommendations"],
            points_manager
        )
    
    st.divider()
    
    # ==================== 我的优惠券区 ====================
    st.subheader("🎫 我的优惠券")
    _render_my_coupons(points_manager)
    
    st.divider()
    
    # ==================== 积分记录区 ====================
    st.subheader("📋 积分记录")
    _render_points_history(points_manager)


def _render_points_overview(summary: dict):
    """
    渲染积分概览区。
    
    Args:
        summary: 积分摘要字典
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 当前积分", f"{summary.get('total_points', 0)} 分")
    
    with col2:
        st.metric("📈 累计获得", f"{summary.get('lifetime_points', 0)} 分")
    
    with col3:
        st.metric("🎫 已兑换", f"{summary.get('exchanged_count', 0)} 张")
    
    with col4:
        st.metric("✅ 可用", f"{summary.get('available_count', 0)} 张")


def _run_coupon_recommendation_flow(
    user_id: str,
    points_manager: PointsManager,
    coupon_repo: CouponRepository,
    profile_manager: UserProfileManager
):
    """
    运行优惠券推荐流程，带可视化步骤展示。
    参考财商助手页面的 Agent 过程展示设计。
    
    Args:
        user_id: 用户 ID
        points_manager: 积分管理器
        coupon_repo: 优惠券仓库
        profile_manager: 用户画像管理器
    """
    # 创建状态占位符
    status_placeholder = st.empty()
    result_placeholder = st.empty()
    
    with status_placeholder:
        with st.status("🧠 AI 正在为你分析...", expanded=True) as status:
            # 步骤 1：读取用户画像
            st.write("⏳ 正在读取你的用户画像...")
            time.sleep(0.5)
            
            try:
                user_profile = profile_manager.get_profile()
                profile_summary = f"{user_profile.get('economic_stage', '未知')}阶段"
                if user_profile.get('current_goal'):
                    profile_summary += f"，目标是{user_profile.get('current_goal')}"
                st.write(f"✅ 读取完成：{profile_summary}")
            except Exception as e:
                st.write(f"⚠️ 读取默认画像")
            
            # 步骤 2：分析消费习惯
            st.write("⏳ 正在分析最近 30 天消费习惯...")
            time.sleep(0.5)
            
            try:
                from utils.data_handler import UserDataManager
                data_manager = UserDataManager(user_id)
                from datetime import datetime, timedelta
                
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                builder = FinanceEvidencePackBuilder(user_id)
                task = {
                    "intent": "coupon_recommendation",
                    "time_range": {
                        "type": "custom",
                        "start_date": start_date,
                        "end_date": end_date,
                        "label": f"{start_date} 至 {end_date}"
                    }
                }
                evidence_pack = builder.build(task)
                
                # 从 selected_summary 中提取用户的消费类别和子类别列表
                selected_summary = evidence_pack.get("selected_summary", {})
                top_categories_list = selected_summary.get("top_categories", [])  # [{name: "餐饮", ...}, ...]
                top_subcategories_list = selected_summary.get("top_subcategories", [])  # [{name: "奶茶", ...}, ...]
                
                # 转换为字符串列表供匹配使用
                top_category_names = [cat["name"] for cat in top_categories_list]  # ["餐饮", "购物", ...]
                top_subcategory_names = [subcat["name"] for subcat in top_subcategories_list]  # ["奶茶", "咖啡", ...]
                
                habit_summary = f"主要消费：{'、'.join(top_category_names[:3]) if top_category_names else '暂无数据'}"
                st.write(f"✅ 分析完成：{habit_summary}")
            except Exception as e:
                st.write(f"⚠️ 使用默认消费习惯")
                top_category_names = []
                top_subcategory_names = []
            
            # 步骤 3：匹配优惠券
            st.write("⏳ 正在从优惠券库匹配...")
            time.sleep(0.5)
            
            try:
                all_coupons = coupon_repo.load_all_coupons()
                matched_count = len(all_coupons)
                st.write(f"✅ 匹配完成：找到 {matched_count} 张可用优惠券")
            except Exception as e:
                st.write(f"⚠️ 匹配失败")
            
            # 步骤 4：生成个性化推荐
            st.write("⏳ 正在生成个性化推荐...")
            time.sleep(0.5)
            
            try:
                # 简单推荐逻辑：根据消费类别匹配
                recommendations = _generate_simple_recommendations(
                    coupon_repo=coupon_repo,
                    points_balance=points_manager.get_balance(),
                    top_category_names=top_category_names,
                    top_subcategory_names=top_subcategory_names
                )
                st.write(f"✅ 推荐生成完毕！为你精选 {len(recommendations)} 张优惠券")
            except Exception as e:
                st.write(f"⚠️ 推荐生成失败，使用默认推荐")
                recommendations = coupon_repo.load_all_coupons()[:5]
            
            # 保存推荐结果
            st.session_state["coupon_recommendations"] = recommendations
            st.session_state["show_recommendation_result"] = True
            st.session_state["recommendation_in_progress"] = False
    
    # 清空状态占位符
    time.sleep(0.3)
    status_placeholder.empty()
    
    # 触发 rerun 以更新界面
    st.rerun()


def _generate_simple_recommendations(
    coupon_repo: CouponRepository,
    points_balance: int,
    top_category_names: list,
    top_subcategory_names: list
) -> list:
    """
    生成简单推荐（不依赖 AI 模型，基于规则的快速推荐）。
    在 MVP 阶段使用此方法，后续可替换为真正的 Agent 驱动推荐。
    
    Args:
        coupon_repo: 优惠券仓库
        points_balance: 当前积分余额
        top_category_names: 用户主要消费类别名列表，如 ["餐饮", "购物", "娱乐"]
        top_subcategory_names: 用户主要消费子类别名列表，如 ["奶茶", "咖啡", "外卖"]
    
    Returns:
        list: 推荐优惠券列表（保证至少返回5张或所有可用优惠券）
    """
    all_coupons = coupon_repo.load_all_coupons()
    
    # 过滤：积分足够的优惠券
    affordable = [c for c in all_coupons if c.get("points_cost", 0) <= points_balance]
    
    # 如果没有积分足够的优惠券，返回所有优惠券（标记为积分不足）
    if not affordable:
        return all_coupons[:5]
    
    # 根据消费类别和子类别匹配
    matched = []
    for coupon in affordable:
        target_match = coupon.get("target_match", {})
        # 优惠券的目标匹配配置
        coupon_focus_categories = target_match.get("focus_categories", [])
        coupon_focus_subcategories = target_match.get("focus_subcategories", [])
        coupon_tags = coupon.get("tags", [])
        
        # 匹配分数（越高表示越匹配）
        match_score = 0
        match_reasons = []
        
        # 1. 检查主要消费类别是否匹配（权重：+3）
        # 同时检查 focus_categories 和 focus_subcategories（因为很多优惠券只配了 subcategories）
        for user_cat in top_category_names:
            if user_cat in coupon_focus_categories:
                match_score += 3
                match_reasons.append(f"主要消费「{user_cat}」")
            # 也检查 category 是否在子类别配置中（有些优惠券用 subcategories 代替 categories）
            if user_cat in coupon_focus_subcategories:
                match_score += 2  # 子类别中匹配到父类别，分数稍低
                match_reasons.append(f"相关消费「{user_cat}」")
        
        # 2. 检查子类别是否匹配（子类别匹配权重更高：+5）
        for user_subcat in top_subcategory_names:
            if user_subcat in coupon_focus_subcategories:
                match_score += 5
                match_reasons.append(f"高频消费「{user_subcat}」")
            # 也检查子类别是否包含在优惠券的标签中（+2）
            if user_subcat in coupon_tags:
                match_score += 2
                match_reasons.append(f"标签相关「{user_subcat}」")
        
        # 3. 检查 problem_signals 是否匹配（+4，高权重）
        problem_signals = target_match.get("problem_signals", [])
        for user_subcat in top_subcategory_names:
            for prob_sig in problem_signals:
                # 部分匹配（如果 problem_signal 包含用户的高频子类别关键词）
                if user_subcat in prob_sig or prob_sig in user_subcat:
                    match_score += 4
                    match_reasons.append(f"问题相关「{user_subcat}」")
        
        # 记录匹配原因（即使分数为0也要记录）
        if match_reasons:
            coupon["match_reason"] = "、".join(match_reasons[:2])  # 最多显示2个原因
        else:
            coupon["match_reason"] = "适合你的优惠券"
        coupon["_match_score"] = match_score
        matched.append(coupon)
    
    # 按匹配分数排序（分数高的在前）
    matched.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
    
    # 保证至少返回 5 张优惠券（如果可用的话）
    if len(matched) < 5:
        # 补充更多优惠券（按积分成本从低到高排序）
        remaining = [c for c in affordable if c not in matched]
        remaining.sort(key=lambda x: x.get("points_cost", 0))
        matched.extend(remaining[:5 - len(matched)])
    
    # 返回最多 5 张
    return matched[:5]


def _render_recommendations(recommendations: list, points_manager: PointsManager):
    """
    渲染推荐优惠券列表。
    
    Args:
        recommendations: 推荐优惠券列表
        points_manager: 积分管理器
    """
    current_points = points_manager.get_balance()
    
    st.markdown("### 🎫 AI 为你推荐")
    
    for i, coupon in enumerate(recommendations):
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                emoji = coupon.get("emoji", "🎫")
                title = coupon.get("title", "优惠券")
                subtitle = coupon.get("subtitle", "")
                tags = coupon.get("tags", [])
                match_reason = coupon.get("match_reason", "")
                
                st.markdown(f"#### {emoji} {title}")
                if subtitle:
                    st.caption(subtitle)
                
                # 标签
                if tags:
                    tag_str = " ".join([f"`{t}`" for t in tags[:3]])
                    st.markdown(f"**标签**: {tag_str}")
                
                # 推荐理由
                if match_reason:
                    st.markdown(f"💭 **推荐理由**: {match_reason}")
                
                # 积分成本
                points_cost = coupon.get("points_cost", 0)
                original_value = coupon.get("original_value", 0)
                st.markdown(f"📦 **需要 {points_cost} 积分** | 预估节省 ¥{original_value}")
            
            with col2:
                # 检查积分是否足够
                can_afford = current_points >= points_cost
                
                if can_afford:
                    if st.button("✅ 可兑换", key=f"exchange_{i}", use_container_width=True):
                        _handle_coupon_exchange(coupon, points_manager)
                        st.rerun()
                else:
                    st.button("❌ 积分不足", key=f"no_afford_{i}", disabled=True, use_container_width=True)
                
                if st.button("⏭️ 跳过", key=f"skip_{i}", use_container_width=True):
                    st.rerun()
            
            st.divider()
    
    # 换一批按钮
    if st.button("🔄 换一批推荐"):
        st.session_state["show_recommendation_result"] = False
        st.session_state["recommendation_in_progress"] = True
        st.rerun()


def _handle_coupon_exchange(coupon: dict, points_manager: PointsManager):
    """
    处理优惠券兑换。
    
    Args:
        coupon: 优惠券信息
        points_manager: 积分管理器
    """
    coupon_id = coupon.get("coupon_id")
    coupon_title = coupon.get("title")
    points_cost = coupon.get("points_cost", 0)
    
    # 扣除积分
    deduct_result = points_manager.deduct_points(points_cost, f"兑换 {coupon_title}")
    
    if deduct_result.get("success"):
        # 添加优惠券记录
        exchange_result = points_manager.add_exchanged_coupon(
            coupon_id=coupon_id,
            coupon_title=coupon_title,
            points_spent=points_cost
        )
        
        if exchange_result.get("success"):
            coupon_code = exchange_result.get("coupon_code", "COUPON_XXXX")
            st.success(f"🎉 兑换成功！")
            st.info(f"优惠券码：**{coupon_code}**")
            st.info(f"请在有效期内使用，预计可节省 ¥{coupon.get('original_value', 0)}")
        else:
            st.error("优惠券记录失败")
    else:
        st.error(f"兑换失败：{deduct_result.get('error', '未知错误')}")


def _render_my_coupons(points_manager: PointsManager):
    """
    渲染我的优惠券区域。
    
    Args:
        points_manager: 积分管理器
    """
    available_coupons = points_manager.get_exchanged_coupons(status="available")
    
    if not available_coupons:
        st.info("📭 暂无已兑换的优惠券，快去兑换吧！")
        return
    
    for i, coupon in enumerate(available_coupons):
        with st.container():
            coupon_title = coupon.get("coupon_title", "优惠券")
            coupon_code = coupon.get("code", "")
            exchanged_at = coupon.get("exchanged_at", "")
            
            # 计算有效期
            if exchanged_at:
                try:
                    from datetime import datetime, timedelta
                    exchanged_date = datetime.fromisoformat(exchanged_at.replace("Z", "+00:00"))
                    valid_until = exchanged_date + timedelta(days=30)
                    valid_str = valid_until.strftime("%Y-%m-%d")
                except:
                    valid_str = "长期有效"
            else:
                valid_str = "长期有效"
            
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{coupon_title}**")
                st.caption(f"有效期至 {valid_str}")
            
            with col2:
                # 复制券码按钮
                if st.button("📋 复制券码", key=f"copy_{i}", use_container_width=True):
                    st.code(coupon_code)
                    st.success("券码已显示")
            
            with col3:
                # 使用按钮
                if st.button("✅ 使用", key=f"use_{i}", use_container_width=True):
                    points_manager.use_coupon(coupon.get("exchange_id"))
                    st.success("已标记为已使用")
                    st.rerun()
    
    # 已使用的优惠券
    st.markdown("---")
    st.markdown("**历史记录**")
    
    used_coupons = points_manager.get_exchanged_coupons(status="used")
    if used_coupons:
        for coupon in used_coupons[:5]:
            coupon_title = coupon.get("coupon_title", "优惠券")
            st.caption(f"✅ {coupon_title}")
    else:
        st.caption("暂无已使用的优惠券")


def _render_points_history(points_manager: PointsManager):
    """
    渲染积分记录区域。
    
    Args:
        points_manager: 积分管理器
    """
    history = points_manager.get_history(limit=20)
    
    if not history:
        st.info("暂无积分记录，开始记账获取积分吧！")
        return
    
    for record in history:
        points = record.get("points", 0)
        description = record.get("description", "")
        timestamp = record.get("timestamp", "")
        
        # 格式化时间
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = timestamp[:16] if len(timestamp) > 16 else timestamp
        else:
            time_str = ""
        
        # 积分增减显示
        if points > 0:
            st.markdown(f"➕ **+{points}** {description} | {time_str}")
        else:
            st.markdown(f"➖ **{points}** {description} | {time_str}")
