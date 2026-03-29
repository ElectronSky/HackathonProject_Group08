"""
储蓄与流动资金管理页面
提供储蓄账户和流动资金的查看、转账功能
"""

import streamlit as st
from utils.account_manager import AccountManager


def show_accounts_page():
    """
    储蓄与流动资金管理页面。
    
    功能：
    - 显示当前储蓄账户和流动资金余额
    - 支持储蓄↔流动资金互转（转账）
    - 显示账户变动历史
    """
    # 页面标题
    st.title("💰 储蓄与流动资金")
    st.markdown("管理你的储蓄账户和流动资金，随时掌握财务状况")
    
    # 检查用户是否登录
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("请先登录")
        return
    
    # 初始化账户管理器
    account_manager = AccountManager(user_id)
    
    # ==================== 余额展示区 ====================
    st.markdown("---")
    st.subheader("📊 当前账户状态")
    
    # 获取账户摘要
    summary = account_manager.get_account_summary()
    
    # 三列展示余额
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="🏦 储蓄账户",
            value=f"¥{summary['savings_balance']:,.2f}",
            delta=None
        )
    with col2:
        st.metric(
            label="💳 流动资金",
            value=f"¥{summary['liquid_balance']:,.2f}",
            delta=None
        )
    with col3:
        st.metric(
            label="💰 总资产",
            value=f"¥{summary['total_assets']:,.2f}",
            delta=None
        )
    
    # ==================== 资金转账区 ====================
    st.markdown("---")
    st.subheader("🔄 资金转账")
    
    with st.expander("点击展开转账功能", expanded=True):
        # 展示两个账户当前余额作为参考
        col_savings, col_arrow, col_liquid = st.columns([1, 0.2, 1])
        with col_savings:
            st.markdown(
                f"<div style='text-align: center; padding: 20px; background-color: #f0f8ff; border-radius: 10px;'>"
                f"<h4>🏦 储蓄账户</h4>"
                f"<h2 style='color: #2e7d32;'>¥{summary['savings_balance']:,.2f}</h2>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_arrow:
            st.markdown("<div style='text-align: center; padding-top: 40px;'><h3>⟷</h3></div>", unsafe_allow_html=True)
        with col_liquid:
            st.markdown(
                f"<div style='text-align: center; padding: 20px; background-color: #fff8e1; border-radius: 10px;'>"
                f"<h4>💳 流动资金</h4>"
                f"<h2 style='color: #f57c00;'>¥{summary['liquid_balance']:,.2f}</h2>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        st.markdown("")  # 空行
        
        # 选择转账方向
        transfer_direction = st.radio(
            "选择转账方向",
            ["to_savings", "to_liquid"],
            horizontal=True,
            format_func=lambda x: "💰 存入储蓄账户" if x == "to_savings" else "💸 取出到流动资金",
            key="transfer_direction_radio"
        )
        
        # 输入转账金额
        transfer_amount = st.number_input(
            "💵 转账金额",
            min_value=0.01,
            value=min(100.0, summary['liquid_balance'] if transfer_direction == "to_savings" else summary['savings_balance']),
            step=50.0,
            format="%.2f",
            help="输入要转账的金额"
        )
        
        # 余额提示
        if transfer_direction == "to_savings":
            if transfer_amount > summary['liquid_balance']:
                st.warning(f"⚠️ 流动资金余额不足（当前：¥{summary['liquid_balance']:,.2f}），超出部分将成为负数")
        else:
            if transfer_amount > summary['savings_balance']:
                st.warning(f"⚠️ 储蓄账户余额不足（当前：¥{summary['savings_balance']:,.2f}），超出部分将成为负数")
        
        # 备注输入
        note = st.text_input(
            "📝 备注（可选）",
            placeholder="例如：发工资存入、本月储蓄目标...",
            key="transfer_note_input"
        )
        
        # 转账方向说明
        if transfer_direction == "to_savings":
            st.info("📤 资金将从 **流动资金** 转入 **储蓄账户**")
        else:
            st.info("📥 资金将从 **储蓄账户** 转入 **流动资金**")
        
        # 确认转账按钮
        if st.button("✅ 确认转账", type="primary", use_container_width=True):
            try:
                # 执行转账（储蓄账户变动时，流动资金自动反向变动）
                result = account_manager.adjust_balance(
                    account_type="savings",
                    change_amount=transfer_amount if transfer_direction == "to_savings" else -transfer_amount,
                    note=note if note else ("存入储蓄账户" if transfer_direction == "to_savings" else "取出到流动资金")
                )
                
                # 获取更新后的余额
                updated_summary = account_manager.get_account_summary()
                
                # 构建成功消息
                if transfer_direction == "to_savings":
                    st.success(
                        f"✅ 转账成功！\n\n"
                        f"📤 从流动资金转入储蓄账户 **¥{transfer_amount:,.2f}**\n\n"
                        f"**储蓄账户：** ¥{updated_summary['savings_balance']:,.2f}（+¥{transfer_amount:,.2f}）\n\n"
                        f"**流动资金：** ¥{updated_summary['liquid_balance']:,.2f}（-¥{transfer_amount:,.2f}）"
                    )
                else:
                    st.success(
                        f"✅ 转账成功！\n\n"
                        f"📥 从储蓄账户转入流动资金 **¥{transfer_amount:,.2f}**\n\n"
                        f"**储蓄账户：** ¥{updated_summary['savings_balance']:,.2f}（-¥{transfer_amount:,.2f}）\n\n"
                        f"**流动资金：** ¥{updated_summary['liquid_balance']:,.2f}（+¥{transfer_amount:,.2f}）"
                    )
                
                st.rerun()
                
            except ValueError as e:
                st.error(f"❌ 转账失败：{str(e)}")
            except Exception as e:
                st.error(f"❌ 系统错误：{str(e)}")
    
    # ==================== 储蓄账户历史 ====================
    st.markdown("---")
    st.subheader("📜 储蓄账户变动历史")
    
    savings_history = account_manager.get_account_history("savings", limit=20)
    
    if savings_history:
        # 显示最近的 10 条记录
        display_history = savings_history[-10:] if len(savings_history) > 10 else savings_history
        
        for i, item in enumerate(reversed(display_history)):
            with st.container():
                # 日期、金额、备注分列显示
                col_date, col_change, col_note = st.columns([2, 1, 3])
                
                with col_date:
                    # 格式化日期，只显示日期部分
                    date_str = item.get("date", "")[:10]
                    st.text(f"📅 {date_str}")
                
                with col_change:
                    change_val = item.get("change", 0)
                    if change_val > 0:
                        st.markdown(f":green[**+¥{change_val:,.2f}**]")
                    else:
                        st.markdown(f":red[**¥{change_val:,.2f}**]")
                
                with col_note:
                    note_text = item.get("note", "")
                    source = item.get("source", "")
                    if source == "income_record":
                        st.text(f"💰 {note_text or '收入分配'}")
                    else:
                        st.text(f"✏️ {note_text or '转账'}")
                
                # 分隔线
                if i < len(display_history) - 1:
                    st.markdown("---")
    else:
        st.info("📭 暂无储蓄记录，开始记录你的第一笔收入吧！")
    
    # ==================== 流动资金历史 ====================
    st.markdown("---")
    st.subheader("📜 流动资金变动历史")
    
    liquid_history = account_manager.get_account_history("liquid", limit=20)
    
    if liquid_history:
        # 显示最近的 10 条记录
        display_history = liquid_history[-10:] if len(liquid_history) > 10 else liquid_history
        
        for i, item in enumerate(reversed(display_history)):
            with st.container():
                # 日期、金额、备注分列显示
                col_date, col_change, col_note = st.columns([2, 1, 3])
                
                with col_date:
                    # 格式化日期，只显示日期部分
                    date_str = item.get("date", "")[:10]
                    st.text(f"📅 {date_str}")
                
                with col_change:
                    change_val = item.get("change", 0)
                    if change_val > 0:
                        st.markdown(f":green[**+¥{change_val:,.2f}**]")
                    else:
                        st.markdown(f":red[**¥{change_val:,.2f}**]")
                
                with col_note:
                    note_text = item.get("note", "")
                    source = item.get("source", "")
                    if source == "income_record":
                        st.text(f"💰 {note_text or '收入分配'}")
                    elif source == "expense":
                        st.text(f"🛒 {note_text or '消费支出'}")
                    else:
                        st.text(f"✏️ {note_text or '转账'}")
                
                # 分隔线
                if i < len(display_history) - 1:
                    st.markdown("---")
    else:
        st.info("📭 暂无流动资金记录")
    
    # ==================== 温馨提示 ====================
    st.markdown("---")
    with st.expander("💡 财商小贴士", expanded=False):
        st.markdown("""
        **什么是储蓄账户？**
        储蓄账户用于存放你计划长期保留的资金，比如紧急备用金或特定储蓄目标。
        
        **什么是流动资金？**
        流动资金是你日常生活中可以随时使用的钱，用于支付日常开支。
        
        **转账说明：**
        - 💰 **存入储蓄**：资金从流动资金转入储蓄账户
        - 💸 **取出到流动资金**：资金从储蓄账户转入流动资金
        
        **小建议：**
        - 收入到账后，可以先将一部分存入储蓄账户
        - 建议保留 1-3 个月生活费作为紧急备用金在流动资金中
        - 通过"记账 → 分析 → 储蓄"的循环，逐步建立健康的财务习惯
        """)
