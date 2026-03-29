"""
预算设置页面
在设置页中为每个类别配置每周 / 每月预算上限
"""

import streamlit as st
from agent.tools.agent_tools import get_current_user_id
from utils.category_service import CategoryService
from utils.data_handler import UserDataManager


BUDGET_PERIOD_LABELS = {
    "weekly": "每周限额（元）",
    "monthly": "每月限额（元）",
}

STATUS_META = {
    "normal": {"icon": "✅", "label": "正常"},
    "warning": {"icon": "⚠️", "label": "预警"},
    "over": {"icon": "🚨", "label": "超额"},
}


def _parse_budget_input(raw_value: str, category_name: str, period_label: str):
    """
    将表单中的预算输入解析为浮点数。

    说明：
    - 允许留空，表示该周期不限额；
    - 不允许负数；
    - 出现非法输入时抛出 ValueError，由页面统一提示。
    """
    normalized_value = str(raw_value).strip()
    if not normalized_value:
        return None

    try:
        numeric_value = float(normalized_value)
    except ValueError as exc:
        raise ValueError(f"{category_name} 的{period_label}必须是有效数字") from exc

    if numeric_value < 0:
        raise ValueError(f"{category_name} 的{period_label}不能小于 0")

    return round(numeric_value, 2)


def _render_budget_status_preview(alert_data: dict):
    """
    渲染单个周期的预算状态预览。

    说明：
    - 这个预览是“当前状态预览”，默认按今天所在的周 / 月计算；
    - 页面只展示已经设置了该周期预算的类别；
    - 状态判断完全复用 UserDataManager 的预算计算结果，避免页面层自己重复写规则。
    """
    summary = alert_data["summary"]
    total_budget_categories = summary["total_budget_categories"]

    if total_budget_categories == 0:
        st.info(f"{alert_data['display_label']} 暂无已配置预算的类别。")
        return

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("已设预算类别", total_budget_categories)
    metric_col2.metric("正常", summary["normal_count"])
    metric_col3.metric("预警", summary["warning_count"])
    metric_col4.metric("超额", summary["over_count"])

    if summary["over_count"] > 0:
        st.error(
            f"{alert_data['display_label']} 当前有 {summary['over_count']} 个类别已超额，请优先关注这些支出项。"
        )
    elif summary["warning_count"] > 0:
        st.warning(
            f"{alert_data['display_label']} 当前有 {summary['warning_count']} 个类别已接近预算上限。"
        )
    else:
        st.success(f"{alert_data['display_label']} 当前所有已配置预算类别都在健康范围内。")

    for item in alert_data["all"]:
        status_meta = STATUS_META[item["status"]]
        with st.container():
            st.markdown(
                f"**{status_meta['icon']} {item['category']}** · {status_meta['label']}"
            )
            info_cols = st.columns([1, 1, 1, 1.2])
            info_cols[0].metric("预算", f"¥{item['budget']:.2f}")
            info_cols[1].metric("已用", f"¥{item['spent']:.2f}")

            if item["status"] == "over":
                info_cols[2].metric("超额", f"¥{item['over_amount']:.2f}")
            else:
                info_cols[2].metric("剩余", f"¥{max(item['remaining'], 0):.2f}")

            info_cols[3].metric("使用率", f"{item['usage_ratio'] * 100:.1f}%")

            st.progress(min(item["usage_ratio"], 1.0))
            st.caption(
                f"周期：{item['start_date']} ~ {item['end_date']} ｜ "
                f"统一预警线：{item['warning_threshold'] * 100:.0f}%"
            )
            st.markdown("---")


def show_budget_page():
    """budget 编辑页面"""
    user_id = get_current_user_id()
    manager = UserDataManager(user_id)
    category_service = CategoryService()

    # 预算编辑需要覆盖两类来源：
    # 1. 配置文件中的标准类别；
    # 2. 当前用户历史交易里已经出现过的类别。
    transaction_categories = [
        transaction.get("category", "")
        for transaction in manager.get_all_transactions()
        if transaction.get("category")
    ]
    merged_categories = category_service.get_merged_category_names(transaction_categories)
    budget_settings = manager.get_budget_settings()
    monthly_alerts = manager.get_budget_alerts(period="monthly")
    weekly_alerts = manager.get_budget_alerts(period="weekly")
    warning_threshold = manager.get_budget_warning_threshold()

    st.subheader("💸 Budget 编辑")
    st.caption("为每个已有类别设置每周 / 每月预算；留空表示该周期不限额。")

    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("类别总数", len(merged_categories))
    info_col2.metric("已设置预算类别", len(budget_settings))
    info_col3.metric(
        "预算周期",
        "周 / 月"
    )

    if not merged_categories:
        st.info("当前暂无可设置预算的类别。请先添加交易记录，或检查类别配置文件。")
        return

    st.markdown("---")

    # 使用表单统一提交，避免用户在逐项输入时频繁触发 rerun
    with st.form("budget_settings_form", clear_on_submit=False):
        st.markdown("### 预算设置表")
        st.caption("建议优先填写你最常消费的类别；不需要限制的周期可保持为空。")

        # 用表格化布局提升可读性，不额外引入复杂 UI 组件
        header_cols = st.columns([1.2, 1, 1])
        header_cols[0].markdown("**类别**")
        header_cols[1].markdown("**每周限额**")
        header_cols[2].markdown("**每月限额**")

        form_values = {}

        for category_name in merged_categories:
            category_budget = budget_settings.get(category_name, {})
            row_cols = st.columns([1.2, 1, 1])
            row_cols[0].markdown(f"`{category_name}`")

            # 使用 text_input 而不是 number_input，原因是：
            # number_input 在留空/清空预算值这类场景里交互不够自然；
            # text_input 能更方便地表达“未设置该预算”。
            weekly_value = row_cols[1].text_input(
                "每周限额（元）",
                value="" if category_budget.get("weekly") is None else str(category_budget.get("weekly")),
                placeholder="例如：200",
                key=f"budget_weekly_{category_name}",
                label_visibility="collapsed",
            )
            monthly_value = row_cols[2].text_input(
                "每月限额（元）",
                value="" if category_budget.get("monthly") is None else str(category_budget.get("monthly")),
                placeholder="例如：800",
                key=f"budget_monthly_{category_name}",
                label_visibility="collapsed",
            )

            form_values[category_name] = {
                "weekly": weekly_value,
                "monthly": monthly_value,
            }

        action_col1, action_col2, action_col3 = st.columns([1.2, 1, 2.8])
        save_submitted = action_col1.form_submit_button("💾 保存预算", use_container_width=True)
        clear_submitted = action_col2.form_submit_button("🧹 清空全部", use_container_width=True)

        if save_submitted:
            try:
                cleaned_budget_settings = {}

                for category_name, raw_limits in form_values.items():
                    parsed_limits = {}

                    for period_key, period_label in BUDGET_PERIOD_LABELS.items():
                        parsed_value = _parse_budget_input(
                            raw_limits.get(period_key, ""),
                            category_name,
                            period_label,
                        )
                        if parsed_value is not None:
                            parsed_limits[period_key] = parsed_value

                    # 只保存至少配置了一个预算周期的类别
                    if parsed_limits:
                        cleaned_budget_settings[category_name] = parsed_limits

                manager.update_budget_settings(cleaned_budget_settings)
                st.success("预算设置已保存并同步到当前用户数据。")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        if clear_submitted:
            manager.update_budget_settings({})
            st.success("已清空当前用户的全部预算设置。")
            st.rerun()

    if budget_settings:
        st.markdown("---")
        with st.expander("📌 当前已保存的预算预览", expanded=False):
            for category_name in merged_categories:
                category_budget = budget_settings.get(category_name)
                if not category_budget:
                    continue

                weekly_text = (
                    f"¥{category_budget['weekly']:.2f}"
                    if category_budget.get("weekly") is not None
                    else "未设置"
                )
                monthly_text = (
                    f"¥{category_budget['monthly']:.2f}"
                    if category_budget.get("monthly") is not None
                    else "未设置"
                )
                st.write(f"- {category_name}：每周 {weekly_text}｜每月 {monthly_text}")
    else:
        st.info("你还没有保存任何预算设置。开启后可按类别逐项填写。")

    st.markdown("---")
    st.subheader("📊 当前状态预览")
    st.caption(
        f"这里展示按今天所在周期计算出的预算状态。当前统一预警阈值为 {warning_threshold * 100:.0f}% 。"
    )

    status_tab_monthly, status_tab_weekly = st.tabs(["📅 本月状态", "🗓️ 本周状态"])
    with status_tab_monthly:
        _render_budget_status_preview(monthly_alerts)

    with status_tab_weekly:
        _render_budget_status_preview(weekly_alerts)

