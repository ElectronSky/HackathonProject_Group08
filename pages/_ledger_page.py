"""
账本展示页面
提供交易记录的查看、筛选、编辑功能
"""
import streamlit as st
from utils.data_handler import UserDataManager
from agent.tools.agent_tools import get_current_user_id
from datetime import datetime
import plotly.graph_objects as go
#  streamlit run HACKATHON_AI\hackathon_project\app.py


STATUS_META = {
    "normal": {"icon": "✅", "label": "正常"},
    "warning": {"icon": "⚠️", "label": "预警"},
    "over": {"icon": "🚨", "label": "超额"},
}


def _render_budget_period_detail(alert_data: dict):
    """渲染单个周期的预算提醒详情。"""
    summary = alert_data["summary"]
    if summary["total_budget_categories"] == 0:
        st.info(f"{alert_data['display_label']} 暂无已配置预算的类别。")
        return

    for item in alert_data["all"]:
        status_meta = STATUS_META[item["status"]]
        status_text = f"{status_meta['icon']} {item['category']} · {status_meta['label']}"

        if item["status"] == "over":
            st.error(
                f"{status_text} ｜ 已用 ¥{item['spent']:.2f} / 预算 ¥{item['budget']:.2f} ｜ "
                f"超额 ¥{item['over_amount']:.2f}"
            )
        elif item["status"] == "warning":
            st.warning(
                f"{status_text} ｜ 已用 ¥{item['spent']:.2f} / 预算 ¥{item['budget']:.2f} ｜ "
                f"使用率 {item['usage_ratio'] * 100:.1f}%"
            )
        else:
            st.info(
                f"{status_text} ｜ 已用 ¥{item['spent']:.2f} / 预算 ¥{item['budget']:.2f} ｜ "
                f"剩余 ¥{max(item['remaining'], 0):.2f}"
            )


def _render_budget_alerts(manager: UserDataManager):
    """
    在账本页渲染当前预算提醒。

    展示策略：
    - 顶部先给本周 / 本月的预算摘要；
    - 再在折叠区里给出详细类别状态；
    - 若用户尚未配置预算，则提供轻量引导，不打断原有账本流程。
    """
    budget_settings = manager.get_budget_settings()
    st.markdown("### 📢 当前预算提醒")

    if not budget_settings:
        st.info("你还没有设置预算，可前往“⚙️ 设置 > 💸 budget”配置每周 / 每月预算。")
        return

    monthly_alerts = manager.get_budget_alerts(period="monthly")
    weekly_alerts = manager.get_budget_alerts(period="weekly")
    warning_threshold = manager.get_budget_warning_threshold()

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("本月预警", monthly_alerts["summary"]["warning_count"])
    metric_col2.metric("本月超额", monthly_alerts["summary"]["over_count"])
    metric_col3.metric("本周预警", weekly_alerts["summary"]["warning_count"])
    metric_col4.metric("本周超额", weekly_alerts["summary"]["over_count"])

    if monthly_alerts["summary"]["over_count"] > 0 or weekly_alerts["summary"]["over_count"] > 0:
        st.error(
            f"当前存在预算超额类别。统一预警阈值为 {warning_threshold * 100:.0f}% ，请优先检查已超额的支出项。"
        )
    elif monthly_alerts["summary"]["warning_count"] > 0 or weekly_alerts["summary"]["warning_count"] > 0:
        st.warning(
            f"当前有部分类别已接近预算上限。统一预警阈值为 {warning_threshold * 100:.0f}% 。"
        )
    else:
        st.success("当前本周 / 本月已配置预算类别均处于安全范围内。")

    with st.expander("查看预算提醒详情", expanded=(
            monthly_alerts["summary"]["over_count"] > 0
            or weekly_alerts["summary"]["over_count"] > 0
            or monthly_alerts["summary"]["warning_count"] > 0
            or weekly_alerts["summary"]["warning_count"] > 0
    )):
        detail_tab_monthly, detail_tab_weekly = st.tabs(["📅 本月预算", "🗓️ 本周预算"])
        with detail_tab_monthly:
            _render_budget_period_detail(monthly_alerts)
        with detail_tab_weekly:
            _render_budget_period_detail(weekly_alerts)


def show_ledger_page():
    """账本展示与编辑页面主函数"""
    st.title("📒 我的账本")

    # 使用全局变量获取用户 ID
    user_id = get_current_user_id()
    manager = UserDataManager(user_id)

    # 在账本页顶部展示预算提醒，方便用户在查看账单前先了解本周 / 本月预算状态
    _render_budget_alerts(manager)
    st.markdown("---")

    # 时间线模式开关（新增）
    timeline_mode = st.toggle("📅 时间线模式", value=False)
    
    # ==================== 时间线模式 ====================
    if timeline_mode:
        st.subheader("📊 时间线视图")
        
        # 获取时间线分组数据
        timeline_data = manager.get_transactions_timeline()
        
        if not timeline_data:
            st.info("暂无任何消费记录")
            return
        
        # 遍历每个时间段
        for group in timeline_data:
            period_name = group["period"]
            transactions = group["transactions"]
            
            # 显示时间段标题
            st.markdown(f"### ---- {period_name} ----")
            
            # 遍历该时间段内的所有交易
            for t in transactions:
                # 方案 1：简单文本显示（当前启用）
                #st.write(f"**{t['date']}** | {t['category']} - {t['subcategory']} | ¥{t['amount']} | {t['description']}")
                
                #方案 2：卡片式 UI（已保留但注释掉）
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background-color: #f0f2f6;
                        padding: 15px;
                        border-radius: 10px;
                        margin: 10px 0;
                        border-left: 5px solid #FF6B6B;
                    ">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-weight: bold;">{t['category']} - {t['subcategory']}</span>
                            <span style="color: #FF6B6B; font-weight: bold;">¥{t['amount']}</span>
                        </div>
                        <div style="margin-top: 8px; color: #666;">{t['description']}</div>
                        <div style="margin-top: 8px; font-size: 12px; color: #999;">{t['date']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 时间段分隔线
            st.divider()
        
        return  # 时间线模式结束
    
    # ==================== 普通表格模式 ====================
    
    # 先获取所有交易用于显示类别选项
    all_transactions = manager.get_all_transactions()
    
    if all_transactions:
        categories = ["全部"] + sorted(list(set(t["category"] for t in all_transactions)))
    else:
        categories = ["全部"]
    
    # 初始化日期筛选的 session state
    if "date_filter_enabled" not in st.session_state:
        st.session_state["date_filter_enabled"] = False
    if "start_date" not in st.session_state:
        st.session_state["start_date"] = None
    if "end_date" not in st.session_state:
        st.session_state["end_date"] = None
    
    # 筛选条件 - 移除不必要的回调函数
    
    col1, col2, col3 = st.columns(3)
    
    # Col1: 类别筛选
    with col1:
        filter_category = st.selectbox(
            "🔍 类别筛选", 
            categories,
            index=0,
            key="filter_cat"
        )
    
    # Col2: 排序方式
    with col2:
        sort_by = st.selectbox(
            "排序方式", 
            ["日期倒序", "日期正序", "金额高到低", "金额低到高"],
            index=0,
            key="sort_opt"
        )
    
    # Col3: 日期范围筛选（新增）
    with col3:
        # 如果未启用日期筛选，显示"限定时间"按钮
        if not st.session_state["date_filter_enabled"]:
            if st.button("📅 限定时间", key="date_filter_btn"):
                # 设置标记，触发 rerun 显示日期输入框
                st.session_state["show_date_input"] = True
                st.rerun()
        else:
            # 已启用日期筛选，显示清除按钮
            if st.button("❌ 清除时间筛选", key="clear_date_filter"):
                st.session_state["date_filter_enabled"] = False
                st.session_state["start_date"] = None
                st.session_state["end_date"] = None
                st.rerun()
    
    # 日期输入框区域（在 Col3 下方显示）
    if st.session_state.get("show_date_input", False):
        with st.expander("📅 选择日期范围", expanded=True):
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                new_start_date = st.date_input(
                    "开始日期",
                    value=datetime.now(),
                    key="start_date_input"
                )
            with col_date2:
                new_end_date = st.date_input(
                    "结束日期",
                    value=datetime.now(),
                    key="end_date_input"
                )
            
            col_confirm, col_space = st.columns([1, 4])
            with col_confirm:
                if st.button("✅ 确认筛选", key="date_confirm"):
                    # 保存选中的日期范围到 session state
                    st.session_state["date_filter_enabled"] = True
                    st.session_state["start_date"] = new_start_date
                    st.session_state["end_date"] = new_end_date
                    st.session_state["show_date_input"] = False
                    st.rerun()
            
            with col_space:
                if st.button("取消", key="date_cancel"):
                    st.session_state["show_date_input"] = False
                    st.rerun()
    
    # ==================== 查询数据（支持多条件叠加）====================
    
    # 收集所有激活的筛选条件
    query_params = {}
    
    # 1. 类别筛选（如果启用）
    if filter_category != "全部":
        query_params["category"] = filter_category
    
    # 2. 日期范围筛选（如果启用）
    if st.session_state["date_filter_enabled"] and st.session_state["start_date"]:
        start_str = st.session_state["start_date"].strftime("%Y-%m-%d")
        end_str = st.session_state["end_date"].strftime("%Y-%m-%d")
        query_params["start_date"] = start_str
        query_params["end_date"] = end_str
    
    # 3. 执行查询（可能包含多个筛选条件）
    if query_params:
        transactions = manager.get_transactions_by_filters(**query_params)
    else:
        transactions = all_transactions
    
    # ==================== 排序（始终生效）====================
    if sort_by == "日期倒序":
        transactions.sort(key=lambda x: x["date"], reverse=True)
    elif sort_by == "日期正序":
        transactions.sort(key=lambda x: x["date"])
    elif sort_by == "金额高到低":
        transactions.sort(key=lambda x: x["amount"], reverse=True)
    elif sort_by == "金额低到高":
        transactions.sort(key=lambda x: x["amount"])
    
    # ==================== 显示当前生效的筛选条件 ====================
    active_filters = []
    if filter_category != "全部":
        active_filters.append(f"类别={filter_category}")
    if st.session_state["date_filter_enabled"] and st.session_state["start_date"]:
        start = st.session_state["start_date"].strftime("%Y-%m-%d")
        end = st.session_state["end_date"].strftime("%Y-%m-%d")
        active_filters.append(f"日期={start}~{end}")
    
    if active_filters:
        st.info(f"✅ 当前筛选：{' AND '.join(active_filters)}，共 {len(transactions)} 条记录")
    else:
        st.info(f"📋 显示全部 {len(transactions)} 条记录")
    
    # ==================== 表格展示 ====================
    st.markdown("---")
    st.subheader("消费数据")

    PAGE_SIZE = 15
    total_records = len(transactions)
    total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages > 1:
        with st.container():
            st.markdown('<div style="display:inline-block; font-size:14px;">页码：</div>', unsafe_allow_html=True)
            page_num = st.selectbox(
                "选择页码",
                options=list(range(1, total_pages + 1)),
                index=st.session_state.get("ledger_page_num", 1) - 1,
                key="ledger_page_num_select",
                label_visibility="collapsed"
            )
    else:
        page_num = 1
    start_idx = (page_num - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_records)
    page_transactions = transactions[start_idx:end_idx]

    if total_records > 0:
        header_cols = st.columns([2, 2, 2, 2, 3, 1, 1])
        header_cols[0].markdown("<span style='font-size:14px'><b>日期</b></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<span style='font-size:14px'><b>类别</b></span>", unsafe_allow_html=True)
        header_cols[2].markdown("<span style='font-size:14px'><b>子类别</b></span>", unsafe_allow_html=True)
        header_cols[3].markdown("<span style='font-size:14px'><b>金额</b></span>", unsafe_allow_html=True)
        header_cols[4].markdown("<span style='font-size:14px'><b>描述</b></span>", unsafe_allow_html=True)
        header_cols[5].markdown("")
        header_cols[6].markdown("")

        edit_row_id = st.session_state.get("edit_row_id", None)
        for idx, t in enumerate(page_transactions):
            row_cols = st.columns([2, 2, 2, 2, 3, 1, 1])
            row_cols[0].markdown(f"<span style='font-size:13px'>{t['date']}</span>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<span style='font-size:13px'>{t['category']}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='font-size:13px'>{t['subcategory']}</span>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<span style='font-size:13px'>¥{t['amount']:.2f}</span>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='font-size:13px'>{t['description']}</span>", unsafe_allow_html=True)
            if row_cols[5].button("✏️", key=f"edit_{t['transaction_id']}"):
                st.session_state["edit_row_id"] = t["transaction_id"]
                st.session_state["edit_row_data"] = t
                st.session_state["show_edit_form"] = True
                st.session_state["edit_row_idx"] = idx
                st.rerun()
            if row_cols[6].button("🗑️", key=f"delete_{t['transaction_id']}"):
                if manager.delete_transaction(t["transaction_id"]):
                    st.success("删除成功")
                    st.rerun()
                else:
                    st.error("删除失败")
            # 在当前行下方插入编辑表单
            if st.session_state.get("show_edit_form", False) and edit_row_id == t["transaction_id"]:
                edit_data = st.session_state.get("edit_row_data", {})
                with st.container():
                    with st.form(f"edit_form_{t['transaction_id']}", clear_on_submit=False):
                        st.markdown("### 编辑账单")
                        new_date = st.date_input("日期", value=datetime.strptime(edit_data["date"], "%Y-%m-%d"), key=f"date_{t['transaction_id']}")
                        new_category = st.text_input("类别", value=edit_data["category"], key=f"cat_{t['transaction_id']}")
                        new_subcategory = st.text_input("子类别", value=edit_data["subcategory"], key=f"subcat_{t['transaction_id']}")
                        new_amount = st.number_input("金额", value=edit_data["amount"], min_value=0.0, step=0.01, key=f"amt_{t['transaction_id']}")
                        new_description = st.text_input("描述", value=edit_data["description"], key=f"desc_{t['transaction_id']}")
                        submitted = st.form_submit_button("保存修改")
                        cancel = st.form_submit_button("取消")
                        if submitted:
                            update_dict = {
                                "date": new_date.strftime("%Y-%m-%d"),
                                "category": new_category,
                                "subcategory": new_subcategory,
                                "amount": float(new_amount),
                                "description": new_description
                            }
                            try:
                                manager.update_transaction(edit_data["transaction_id"], update_dict)
                                st.success("修改成功")
                                st.session_state["show_edit_form"] = False
                                st.session_state["edit_row_id"] = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"修改失败: {e}")
                        if cancel:
                            st.session_state["show_edit_form"] = False
                            st.session_state["edit_row_id"] = None
                            st.rerun()
    else:
        st.info("暂无符合条件的数据")

    # ==================== 统计分析区域 ====================
    st.markdown("---")
    st.subheader("📈 数据分析")
    import plotly.graph_objects as go
    # 只有当有交易数据时才显示分析
    if len(transactions) > 0:
        # 获取统计结果
        statistics = manager.get_statistics_by_filter(
            start_date=query_params.get("start_date"),
            end_date=query_params.get("end_date")
        )
        
        # 计算总金额和总交易数
        total_amount = sum(t["amount"] for t in transactions)
        transaction_count = len(transactions)
        avg_amount = total_amount / transaction_count if transaction_count > 0 else 0
        
        # 第一级：概览卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总支出", f"¥{total_amount:.2f}")
        with col2:
            st.metric("交易数量", f"{transaction_count}笔")
        with col3:
            st.metric("平均单笔", f"¥{avg_amount:.2f}")
        with col4:
            # 计算最大单笔支出
            max_amount = max(t["amount"] for t in transactions)
            st.metric("最大单笔", f"¥{max_amount:.2f}")
        
        # 第二级：主要分类统计
        with st.expander("📊 按类别分析", expanded=True):
            if statistics["category_stats"]:
                chart_col, pie_col = st.columns([2, 2])
                with chart_col:
                    # 保留原有柱状图
                    category_data = {}
                    for category, stats in statistics["category_stats"].items():
                        category_data[category] = stats["total_amount"]
                    st.bar_chart(category_data)
                    # 详细数据文字展示
                    st.write("**详细数据**")
                    for category, stats in statistics["category_stats"].items():
                        percent = statistics["amount_ratio"][category] * 100
                        st.write(f"- {category}: ¥{stats['total_amount']:.2f} ({percent:.1f}%)")
                with pie_col:
                    # 饼图
                    labels = []
                    values = []
                    text = []
                    for category, stats in statistics["category_stats"].items():
                        labels.append(category)
                        values.append(stats["total_amount"])
                        percent = statistics["amount_ratio"][category] * 100
                        text.append(f"{category}: ¥{stats['total_amount']:.2f} ({percent:.1f}%)")
                    fig = go.Figure(data=[go.Pie(labels=labels, values=values, text=text, textinfo='label+percent', hoverinfo='text', hole=0.3)])
                    fig.update_traces(textposition='inside', textfont_size=14)
                    fig.update_traces(textfont=dict(color='black'), insidetextfont=dict(color='black'), outsidetextfont=dict(color='black'))
                    fig.update_layout(legend=dict(font=dict(color='black')), margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
        
        # 第三级：时间趋势分析
        with st.expander("📉 时间趋势分析", expanded=False):
            time_type = st.radio("查看维度", ["月度", "周度"], horizontal=True)

            if time_type == "月度" and statistics["time_stats"]["monthly"]:
                # 准备月度数据
                monthly_data = {}
                for month in sorted(statistics["time_stats"]["monthly"].keys()):
                    monthly_data[month] = statistics["time_stats"]["monthly"][month]["total_amount"]
                # 柱状图
                st.bar_chart(monthly_data)
                # 详细数据与饼图
                detail_col, pie_col = st.columns([2, 1])
                with detail_col:
                    st.write("**月度详细数据**")
                    month_labels = []
                    month_values = []
                    month_text = []
                    for month in sorted(statistics["time_stats"]["monthly"].keys()):
                        stats = statistics["time_stats"]["monthly"][month]
                        ratio = statistics["time_amount_ratio"]["monthly"][month] * 100
                        st.write(f"- {month}: ¥{stats['total_amount']:.2f} ({ratio:.1f}%)")
                        month_labels.append(month)
                        month_values.append(stats["total_amount"])
                        month_text.append(f"{month}: ¥{stats['total_amount']:.2f} ({ratio:.1f}%)")

                with pie_col:
                    fig_month = go.Figure(data=[go.Pie(labels=month_labels, values=month_values, text=month_text, textinfo='label+percent', hoverinfo='text', hole=0.3)])
                    fig_month.update_traces(textposition='inside', textfont_size=14)
                    # 设置饼图内文字为黑色
                    fig_month.update_traces(textfont=dict(color='black'), insidetextfont=dict(color='black'), outsidetextfont=dict(color='black'))
                    fig_month.update_layout(legend=dict(font=dict(color='black')), margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_month, use_container_width=True)

            elif time_type == "周度" and statistics["time_stats"]["weekly"]:
                # 准备周度数据
                weekly_data = {}
                for week in sorted(statistics["time_stats"]["weekly"].keys()):
                    weekly_data[week] = statistics["time_stats"]["weekly"][week]["total_amount"]
                st.bar_chart(weekly_data)
                detail_col, pie_col = st.columns([2, 1])
                with detail_col:
                    st.write("**周度详细数据**")
                    week_labels = []
                    week_values = []
                    week_text = []
                    for week in sorted(statistics["time_stats"]["weekly"].keys()):
                        stats = statistics["time_stats"]["weekly"][week]
                        ratio = statistics["time_amount_ratio"]["weekly"][week] * 100
                        st.write(f"- {week}: ¥{stats['total_amount']:.2f} ({ratio:.1f}%)")
                        week_labels.append(week)
                        week_values.append(stats["total_amount"])
                        week_text.append(f"{week}: ¥{stats['total_amount']:.2f} ({ratio:.1f}%)")
                with pie_col:
                    # 周度饼图
                    fig_week = go.Figure(data=[go.Pie(labels=week_labels, values=week_values, text=week_text, textinfo='label+percent', hoverinfo='text', hole=0.3)])
                    fig_week.update_traces(textposition='inside', textfont_size=14)
                    # 设置饼图内文字为黑色
                    fig_week.update_traces(textfont=dict(color='black'), insidetextfont=dict(color='black'), outsidetextfont=dict(color='black'))
                    fig_week.update_layout(legend=dict(font=dict(color='black')), margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_week, use_container_width=True)
        # 第四级：金额区间分析
        with st.expander("💰 金额区间分析", expanded=False):
            # 准备金额区间数据
            level_labels = []
            level_values = []
            level_text = []
            for level, ratio in statistics["amount_level_ratio"].items():
                count = sum(1 for t in transactions if 
                           (level == "10元及以下" and t["amount"] <= 10) or
                           (level == "10到50元" and 10 < t["amount"] <= 50) or
                           (level == "50到100元" and 50 < t["amount"] <= 100) or
                           (level == "100到300元" and 100 < t["amount"] <= 300) or
                           (level == "300到1000元" and 300 < t["amount"] <= 1000) or
                           (level == "1000元以上" and t["amount"] > 1000))
                level_labels.append(level)
                level_values.append(count)
                level_text.append(f"{level}: {count}笔 ({ratio*100:.1f}%)")
            fig2 = go.Figure(data=[go.Pie(labels=level_labels, values=level_values, text=level_text, textinfo='label+percent', hoverinfo='text', hole=0.3)])
            fig2.update_traces(textposition='inside', textfont_size=14)
            fig2.update_traces(textfont=dict(color='black'), insidetextfont=dict(color='black'), outsidetextfont=dict(color='black'))
            fig2.update_layout(legend=dict(font=dict(color='black')), margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig2, use_container_width=True)
            st.write("**金额区间详细数据**")
            for i, level in enumerate(level_labels):
                st.write(level_text[i])
