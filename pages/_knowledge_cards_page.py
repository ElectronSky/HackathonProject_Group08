"""
知识卡片浏览页面
用户可以查看全部卡片、历史卡片和正在学习中的卡片。
"""

import streamlit as st
from datetime import datetime

try:
    from ..agent.tools.agent_tools import get_current_user_id
    from ..utils.card_repository import CardRepository
    from ..utils.card_state_manager import CardStateManager
except ImportError:
    from importlib import import_module

    get_current_user_id = import_module("agent.tools.agent_tools").get_current_user_id
    CardRepository = import_module("utils.card_repository").CardRepository
    CardStateManager = import_module("utils.card_state_manager").CardStateManager


def _get_status_display_info(status: str) -> tuple[str, str]:
    """
    根据卡片状态返回显示标签和颜色。
    """
    status_map = {
        "active": ("🟢 正在学习", "success"),
        "snoozed": ("🟡 稍后提醒", "warning"),
        "completed": ("✅ 已完成", "complete"),
        "archived": ("📋 历史记录", "info"),
    }
    return status_map.get(status, ("❓ 未知状态", "off"))


def _format_datetime(dt_str: str) -> str:
    """
    格式化日期时间字符串，只保留日期部分便于显示。
    """
    if not dt_str:
        return "未知"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return dt_str[:16] if len(dt_str) >= 16 else dt_str


def _render_card_detail(card_data: dict, show_instance_info: bool = False, state_manager=None):
    """
    渲染单张卡片的详细信息。
    
    Args:
        card_data: 卡片数据字典
        show_instance_info: 是否显示实例信息（如加入时间、评估状态等）
        state_manager: 状态管理器（用于笔记和状态切换功能）
    """
    # 标题和标签
    st.markdown(f"### 📚 {card_data.get('title', '未命名卡片')}")
    
    tags = card_data.get("tags", [])
    if tags:
        st.caption(" ".join(f"`#{tag}`" for tag in tags))
    
    st.markdown("---")
    
    # 基本信息区域
    col1, col2 = st.columns(2)
    
    with col1:
        # 做什么
        st.markdown("**🎯 做什么**")
        st.info(card_data.get("doing_text", "暂无"))
        
        # 专业名词
        professional_term = str(card_data.get("professional_term", "")).strip()
        if professional_term:
            st.markdown(f"**📖 专业名词**：`{professional_term}`")
    
    with col2:
        # 为什么
        st.markdown("**💡 为什么**")
        st.write(card_data.get("why_text", "暂无"))
        
        # 权威来源
        authority_source = str(card_data.get("authority_source", "")).strip()
        if authority_source:
            with st.expander("📚 权威依据"):
                st.caption(authority_source)
    
    st.markdown("---")
    
    # 如果是用户实例卡片，显示实例相关信息
    if show_instance_info and state_manager:
        instance_info = card_data.get("instance_info", {})
        card_instance_id = instance_info.get("card_instance_id", "")
        
        if instance_info and card_instance_id:
            # 基本信息一行
            current_status = instance_info.get("status", "unknown")
            status_label, _ = _get_status_display_info(current_status)
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                # 初次加入时间
                activated_at = instance_info.get("activated_at", "")
                if activated_at:
                    st.caption(f"📅 加入：{_format_datetime(activated_at)}")
            
            with col_info2:
                # 当前状态
                st.caption(f"📌 {status_label}")
            
            with col_info3:
                # 下次评估时间
                next_eval = instance_info.get("next_evaluation_date", "")
                if next_eval:
                    try:
                        next_dt = datetime.strptime(next_eval, "%Y-%m-%d").date()
                        today = datetime.now().date()
                        days_left = (next_dt - today).days
                        if days_left < 0:
                            st.caption(f"⏰ 已到期：{next_eval}")
                        elif days_left == 0:
                            st.caption(f"📆 今天可评估")
                        else:
                            st.caption(f"📆 {next_eval}（剩{days_left}天）")
                    except ValueError:
                        st.caption(f"📆 {next_eval}")
            
            st.markdown("---")
            
            # 学习笔记区域
            st.markdown("**📝 学习笔记**")
            
            # 获取当前笔记
            current_note = instance_info.get("note", "") or ""
            note_updated_at = instance_info.get("note_updated_at", "") or ""
            
            # 初始化session_state控制笔记编辑区域展开状态
            note_edit_key = f"note_edit_mode_{card_instance_id}"
            if note_edit_key not in st.session_state:
                st.session_state[note_edit_key] = False
            
            # 如果有笔记，显示笔记内容
            if current_note:
                st.info(current_note)
                if note_updated_at:
                    st.caption(f"最后修改：{_format_datetime(note_updated_at)}")
            else:
                st.caption("💬 用户尚未添加过该卡片的笔记")
            
            # 新建/修改笔记按钮
            if not st.session_state[note_edit_key]:
                if st.button("📝 新建/修改笔记", key=f"note_toggle_{card_instance_id}", use_container_width=True):
                    st.session_state[note_edit_key] = True
                    st.rerun()
            else:
                # 笔记编辑区域（展开状态）
                note_text = st.text_area(
                    "输入你的学习笔记...",
                    value=current_note,
                    height=100,
                    key=f"note_input_{card_instance_id}",
                    label_visibility="collapsed",
                    placeholder="例如：我打算从明天开始每周只喝2次奶茶..."
                )
                
                col_note1, col_note2 = st.columns([1, 4])
                with col_note1:
                    if st.button("💾 保存", key=f"save_note_{card_instance_id}", use_container_width=True):
                        if state_manager.update_card_note(card_instance_id, note_text):
                            st.session_state[note_edit_key] = False
                            st.success("笔记已保存！")
                            st.rerun()
                        else:
                            st.error("保存失败")
                
                with col_note2:
                    if st.button("❌ 取消", key=f"cancel_note_{card_instance_id}", use_container_width=True):
                        st.session_state[note_edit_key] = False
                        st.rerun()
            
            st.markdown("---")
            
            # 评估信息（可折叠）
            with st.expander("📊 评估信息"):
                # 评估条件
                evaluation_desc = card_data.get("evaluation_description", "")
                if evaluation_desc:
                    st.markdown("**评估条件**")
                    st.write(evaluation_desc)
                
                # 改进提示
                improvement_hint = card_data.get("improvement_hint", "")
                if improvement_hint:
                    st.markdown("**关注重点**")
                    st.write(improvement_hint)
                
                # 评估历史
                eval_history = instance_info.get("evaluation_history", [])
                if eval_history:
                    st.markdown(f"**评估历史（共 {len(eval_history)} 次）**")
                    for i, record in enumerate(eval_history[-3:], 1):
                        eval_at = _format_datetime(record.get("evaluated_at", ""))
                        result = record.get("evaluation_result", "unknown")
                        st.markdown(f"- 第 {i} 次 ({eval_at})：{result}")
            
            # 修改卡片状态（可折叠）
            status_edit_key = f"status_edit_{card_instance_id}"
            with st.expander("✏️ 修改卡片状态"):
                st.markdown("**修改卡片状态**")
                
                # 状态切换按钮
                status_col1, status_col2, status_col3 = st.columns(3)
                
                with status_col1:
                    if current_status != "active":
                        if st.button("🟢 正在学习", key=f"status_active_{card_instance_id}", use_container_width=True):
                            if state_manager.update_card_status(card_instance_id, "active"):
                                st.success("已切换到「正在学习」")
                                st.rerun()
                            else:
                                st.error("切换失败")
                
                with status_col2:
                    if current_status != "snoozed":
                        if st.button("🟡 稍后提醒", key=f"status_snoozed_{card_instance_id}", use_container_width=True):
                            if state_manager.update_card_status(card_instance_id, "snoozed"):
                                st.success("已切换到「稍后提醒」")
                                st.rerun()
                            else:
                                st.error("切换失败")
                
                with status_col3:
                    if current_status not in ["archived", "completed"]:
                        if st.button("📋 移入历史", key=f"status_archive_{card_instance_id}", use_container_width=True):
                            if state_manager.update_card_status(card_instance_id, "archived"):
                                st.success("已移入历史记录")
                                st.rerun()
                            else:
                                st.error("操作失败")


def _render_all_cards_view(repository: CardRepository, state_manager: CardStateManager):
    """
    渲染"全部卡片"视图
    展示本地数据库中的所有卡片，包括从未被推荐过的和已被用户互动过的。
    """
    st.markdown("### 📚 全部知识卡片")
    st.caption("本地卡片库中的所有知识卡片，包括历史卡片和还未被推荐过的卡片。")
    
    all_cards = repository.load_all_cards()
    if not all_cards:
        st.info("当前卡片库为空，暂无知识卡片。")
        return
    
    # 获取用户已经互动过的卡片实例
    active_cards = state_manager.get_active_cards()
    archived_cards = state_manager.get_archived_cards()
    
    # 构建 card_id -> instance_info 的映射
    instance_map = {}
    for card in active_cards + archived_cards:
        card_id = card.get("card_id", "")
        if card_id:
            instance_map[card_id] = card
    
    # 按标签分组展示
    st.markdown("---")
    
    for i, card in enumerate(all_cards):
        card_id = card.get("card_id", "")
        
        # 检查是否在用户的学习历史中
        instance_info = instance_map.get(card_id, {})
        
        # 构建展示数据
        display_data = {**card}
        if instance_info:
            display_data["instance_info"] = instance_info
        
        with st.expander(f"📖 {card.get('title', '未命名')} {'' if instance_info else '（未被推荐过）'}"):
            _render_card_detail(display_data, show_instance_info=bool(instance_info), state_manager=state_manager if instance_info else None)


def _render_history_cards_view(state_manager: CardStateManager, repository: CardRepository):
    """
    渲染"历史卡片"视图
    展示用户曾经互动过的所有卡片（包含活跃中和已完成的）。
    """
    st.markdown("### 📋 历史卡片")
    st.caption("你曾经互动过的知识卡片，包括正在学习和已完成的卡片。")
    
    active_cards = state_manager.get_active_cards()
    archived_cards = state_manager.get_archived_cards()
    
    all_history = active_cards + archived_cards
    
    if not all_history:
        st.info("你还没有互动过任何知识卡片。快去 AI 财商助手发起分析，获取推荐吧！")
        return
    
    # 按加入时间倒序排列
    all_history.sort(key=lambda x: x.get("activated_at") or "", reverse=True)
    
    for i, card_instance in enumerate(all_history):
        card_id = card_instance.get("card_id", "")
        card_data = repository.get_card_by_id(card_id)
        
        if not card_data:
            continue
        
        status = card_instance.get("status", "unknown")
        status_label, _ = _get_status_display_info(status)
        
        with st.expander(f"{status_label} {card_data.get('title', '未命名')}"):
            # 构建展示数据
            display_data = {**card_data, "instance_info": card_instance}
            _render_card_detail(display_data, show_instance_info=True, state_manager=state_manager)


def _render_active_cards_view(state_manager: CardStateManager, repository: CardRepository):
    """
    渲染"正在学习"视图
    只展示用户当前正在追踪学习的卡片。
    """
    st.markdown("### 🔄 正在学习")
    st.caption("你当前正在追踪学习的知识卡片，记得按时评估哦！")
    
    active_cards = state_manager.get_active_cards()
    
    if not active_cards:
        st.info("你目前没有正在学习的卡片。快去 AI 财商助手发起分析，获取推荐吧！")
        return
    
    # 按下次评估时间排序（即将到期的排前面）
    def sort_key(x):
        next_date = x.get("next_evaluation_date") or "9999-12-31"
        return next_date
    
    active_cards.sort(key=sort_key)
    
    # 显示即将到期的卡片
    today = datetime.now().date()
    urgent_cards = []
    upcoming_cards = []
    
    for card in active_cards:
        next_date_str = card.get("next_evaluation_date", "")
        if next_date_str:
            try:
                next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date()
                days_left = (next_date - today).days
                if days_left <= 3:
                    urgent_cards.append((days_left, card))
                else:
                    upcoming_cards.append((days_left, card))
            except ValueError:
                upcoming_cards.append((999, card))
        else:
            upcoming_cards.append((999, card))
    
    # 即将到期的卡片
    if urgent_cards:
        st.warning("⏰ 以下卡片即将到期，建议尽快评估：")
        for days_left, card_instance in urgent_cards:
            card_id = card_instance.get("card_id", "")
            card_data = repository.get_card_by_id(card_id)
            if card_data:
                with st.expander(f"⚠️ {card_data.get('title', '未命名')}（还剩 {days_left} 天）"):
                    display_data = {**card_data, "instance_info": card_instance}
                    _render_card_detail(display_data, show_instance_info=True, state_manager=state_manager)
    
    # 正常状态的卡片
    if upcoming_cards:
        if urgent_cards:
            st.markdown("---")
        for days_left, card_instance in upcoming_cards:
            card_id = card_instance.get("card_id", "")
            card_data = repository.get_card_by_id(card_id)
            if card_data:
                time_info = f"（还剩 {days_left} 天）" if days_left < 999 else "（评估日期未设置）"
                with st.expander(f"📖 {card_data.get('title', '未命名')}{time_info}"):
                    display_data = {**card_data, "instance_info": card_instance}
                    _render_card_detail(display_data, show_instance_info=True, state_manager=state_manager)


def show_knowledge_cards_page():
    """
    知识卡片浏览页面主函数。
    """
    st.title("📚 知识卡片库")
    st.caption("浏览和追踪你的财商知识学习进度")
    
    # 检查用户是否登录
    try:
        user_id = get_current_user_id()
    except Exception:
        st.warning("请先登录后再访问知识卡片库。")
        return
    
    # 初始化仓库和管理器
    repository = CardRepository()
    state_manager = CardStateManager(user_id)
    
    # 统计信息
    active_count = len(state_manager.get_active_cards())
    archived_count = len(state_manager.get_archived_cards())
    total_card_count = len(repository.load_all_cards())
    
    # 顶部统计
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    with stat_col1:
        st.metric("📚 卡片库总数", total_card_count)
    with stat_col2:
        st.metric("🔄 正在学习", active_count)
    with stat_col3:
        st.metric("✅ 已完成", archived_count)
    
    st.markdown("---")
    
    # 三种展示模式按钮
    st.markdown("### 选择查看模式")
    
    # 使用按钮组控制展示模式
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    # session_state 控制当前模式
    if "card_view_mode" not in st.session_state:
        st.session_state["card_view_mode"] = "all"
    
    mode = st.session_state["card_view_mode"]
    
    with btn_col1:
        btn_label = "📚 全部卡片"
        if mode == "all":
            btn_label = "📚 全部卡片 ✓"
        if st.button(btn_label, use_container_width=True, type="primary" if mode == "all" else "secondary"):
            st.session_state["card_view_mode"] = "all"
            st.rerun()
    
    with btn_col2:
        btn_label = "📋 历史卡片"
        if mode == "history":
            btn_label = "📋 历史卡片 ✓"
        if st.button(btn_label, use_container_width=True, type="primary" if mode == "history" else "secondary"):
            st.session_state["card_view_mode"] = "history"
            st.rerun()
    
    with btn_col3:
        btn_label = "🔄 正在学习"
        if mode == "active":
            btn_label = "🔄 正在学习 ✓"
        if st.button(btn_label, use_container_width=True, type="primary" if mode == "active" else "secondary"):
            st.session_state["card_view_mode"] = "active"
            st.rerun()
    
    st.markdown("---")
    
    # 根据当前模式渲染对应视图
    current_mode = st.session_state.get("card_view_mode", "all")
    
    if current_mode == "all":
        _render_all_cards_view(repository, state_manager)
    elif current_mode == "history":
        _render_history_cards_view(state_manager, repository)
    elif current_mode == "active":
        _render_active_cards_view(state_manager, repository)
