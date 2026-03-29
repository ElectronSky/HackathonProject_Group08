"""
AI 财商助手页面
负责承接用户的自然语言分析需求，并以聊天式交互驱动财商分析专用 ReAct agent。
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, cast

import streamlit as st

try:
    from ..agent.finance_react_agent import FinanceReactAgent
    from ..agent.tools.agent_tools import get_current_user_id
    from ..utils.card_state_manager import CardStateManager
    from ..utils.conversation_manager import ConversationManager
    from ..utils.user_profile_manager import UserProfileManager
except ImportError:
    from importlib import import_module

    FinanceReactAgent = import_module("agent.finance_react_agent").FinanceReactAgent
    get_current_user_id = import_module("agent.tools.agent_tools").get_current_user_id
    CardStateManager = import_module("utils.card_state_manager").CardStateManager
    ConversationManager = import_module("utils.conversation_manager").ConversationManager
    UserProfileManager = import_module("utils.user_profile_manager").UserProfileManager


def _init_ai_finance_state():
    """
    初始化财商助手页面的独立状态。

    说明：
    - 这些状态和记账页的 `message / current_conversation_id` 分开维护；
    - 这样才能支持两个页面互不串台的独立历史。
    """
    if "finance_messages" not in st.session_state:
        st.session_state["finance_messages"] = []

    if "finance_current_conversation_id" not in st.session_state:
        st.session_state["finance_current_conversation_id"] = None

    if "finance_editing_title" not in st.session_state:
        st.session_state["finance_editing_title"] = False

    if "finance_input_draft" not in st.session_state:
        st.session_state["finance_input_draft"] = ""

    # 这个标记用于规避 Streamlit 的限制：
    # widget 已经实例化后，不能在同一轮脚本里直接修改它对应的 session_state。
    # 因此发送成功后，我们先把“下一轮需要清空输入框”的意图记下来，
    # 再在下一次 rerun、且 text_area 创建之前执行真正的清空。
    if "finance_should_clear_input" not in st.session_state:
        st.session_state["finance_should_clear_input"] = False

    if "finance_pending_card_evaluation" not in st.session_state:
        st.session_state["finance_pending_card_evaluation"] = None

    if "finance_flash_message" not in st.session_state:
        st.session_state["finance_flash_message"] = None

    # 只有在 widget 创建之前，才能安全地重置它绑定的 session_state。
    if st.session_state["finance_should_clear_input"]:
        st.session_state["finance_input_draft"] = ""
        st.session_state["finance_should_clear_input"] = False

    # 当用户已经登录，但页面状态还没有完整初始化时，这里做补全。
    if st.session_state.get("logged_in") and st.session_state.get("finance_agent") is None:
        st.session_state["finance_agent"] = FinanceReactAgent()

    if st.session_state.get("logged_in") and st.session_state.get("finance_conversation_manager") is None:
        st.session_state["finance_conversation_manager"] = ConversationManager(
            st.session_state["user_id"],
            conversation_type="finance"
        )


def _set_demo_query(query_text: str):
    """
    把推荐问题写入输入框草稿，方便用户一键发送。
    """
    st.session_state["finance_input_draft"] = query_text


def _render_finance_sidebar(conv_manager: ConversationManager):
    """
    渲染财商助手独立的对话管理区。
    """
    with st.sidebar:
        st.markdown("---")
        st.subheader("财商助手对话")

        if st.button("🆕 新对话", key="finance_new_conversation", use_container_width=True):
            st.session_state["finance_messages"] = []
            st.session_state["finance_current_conversation_id"] = None
            st.session_state["finance_editing_title"] = False
            st.session_state["finance_input_draft"] = ""
            st.session_state["finance_pending_card_evaluation"] = None
            st.rerun()

        if st.button("📋 卡片评估检查", key="finance_check_card_evaluation", use_container_width=True):
            evaluation_status = _handle_card_evaluation_check(conv_manager)
            if evaluation_status["status"] == "none":
                st.info(evaluation_status["message"])
            else:
                st.rerun()

        current_conv_id = st.session_state["finance_current_conversation_id"]

        if current_conv_id:
            conversations = conv_manager.get_user_conversations()
            current_conv = next((conv for conv in conversations if conv["id"] == current_conv_id), None)

            if current_conv:
                title = current_conv["title"]
                title_col1, title_col2 = st.columns([3, 1])

                with title_col1:
                    if st.session_state["finance_editing_title"]:
                        new_title = st.text_input(
                            "",
                            value=title,
                            label_visibility="collapsed",
                            key="finance_title_input"
                        )
                    else:
                        st.write(f"**{title}**")

                with title_col2:
                    if st.session_state["finance_editing_title"]:
                        if st.button("✅", key="finance_save_title", use_container_width=True):
                            conv_manager.save_current_conversation(
                                st.session_state["finance_messages"],
                                title=new_title,
                                conversation_id=current_conv_id,
                            )
                            st.session_state["finance_editing_title"] = False
                            st.rerun()
                    else:
                        if st.button("✏️", key="finance_edit_title", use_container_width=True):
                            st.session_state["finance_editing_title"] = True
                            st.rerun()
        else:
            st.write("**新对话**")

        st.markdown("### 📜 历史分析对话")
        conversations = conv_manager.get_user_conversations()
        for conversation in conversations:
            col1, col2 = st.columns([3, 1])

            with col1:
                conversation_date = conversation["updated_at"].split("T")[0]
                if st.button(
                    f"💬 {conversation['title']} ({conversation_date})",
                    key=f"finance_load_{conversation['id']}",
                    use_container_width=True,
                ):
                    loaded_messages = conv_manager.load_conversation(conversation["id"])
                    if loaded_messages is not None:
                        st.session_state["finance_messages"] = loaded_messages
                        st.session_state["finance_current_conversation_id"] = conversation["id"]
                        st.session_state["finance_editing_title"] = False
                        st.rerun()

            with col2:
                if st.button("🗑️", key=f"finance_delete_{conversation['id']}", use_container_width=True):
                    if conv_manager.delete_conversation(conversation["id"]):
                        if st.session_state["finance_current_conversation_id"] == conversation["id"]:
                            st.session_state["finance_messages"] = []
                            st.session_state["finance_current_conversation_id"] = None
                            st.session_state["finance_editing_title"] = False
                        st.rerun()


def _render_example_buttons():
    """
    渲染推荐问题按钮，帮助用户快速体验财商助手能力。
    """
    st.markdown("### 快速示例")
    example_col1, example_col2, example_col3, example_col4 = st.columns(4)

    if example_col1.button("上个月消费情况", use_container_width=True):
        _set_demo_query("帮我看看上个月我的消费情况")
        st.rerun()

    if example_col2.button("最近 30 天问题分析", use_container_width=True):
        _set_demo_query("帮我看看我消费有什么问题没有")
        st.rerun()

    if example_col3.button("本月预算执行情况", use_container_width=True):
        _set_demo_query("帮我看看我本月预算执行得怎么样")
        st.rerun()

    if example_col4.button("最近 7 天奶茶情况", use_container_width=True):
        _set_demo_query("帮我看看最近 7 天奶茶喝得多不多")
        st.rerun()

    extra_col1, extra_col2, extra_col3 = st.columns(3)
    if extra_col1.button("全部历史消费概览", use_container_width=True):
        _set_demo_query("帮我看看我的全部消费情况")
        st.rerun()

    if extra_col2.button("过去三个月消费分析", use_container_width=True):
        _set_demo_query("帮我分析我这三个月的消费")
        st.rerun()

    if extra_col3.button("去年 3 月专题分析", use_container_width=True):
        _set_demo_query("帮我分析我去年3月的消费")
        st.rerun()


def _run_finance_agent_with_visual_steps(finance_agent: FinanceReactAgent,
                                         normalized_query: str,
                                         history_before_current_turn: list,
                                         runtime_context: dict) -> dict:
    """
    执行财商 agent，并把工具调用过程以更友好的方式展示在页面上。

    说明：
    - 用户在等待时，不会只看到一个 spinner；
    - 同时你作为开发者，也能更直观看到错误发生在哪一步。
    
    修复说明：
    - 思考时隐藏 AI 头像，只显示进度状态
    - 回答生成后再显示带头像的 chat_message
    """
    # 第一阶段：显示思考进度，AI 头像隐藏
    progress_status = st.status("🤔 AI 正在思考中...", expanded=True)
    progress_status.write("📊 理解你的问题...")

    response_messages = []
    error_detected = False
    artifacts = {}
    
    def capture_answer_events():
        """
        参考你原来在 streamlit 聊天页里抓 chunk 的方式，
        把 answer 事件缓存后再一字符一字符吐给页面。
        """
        nonlocal error_detected
        for event in finance_agent.execute_stream_with_events(
            query=normalized_query,
            history=history_before_current_turn,
            runtime_context=runtime_context,
        ):
            event_type = event.get("type")
            event_content = event.get("content", "")

            if event_type == "status":
                progress_status.write(event_content)
                continue

            if event_type == "error":
                error_detected = True
                progress_status.write(event_content)
                continue

            if event_type == "artifact":
                artifacts[event.get("name", "unknown_artifact")] = event_content
                continue

            if event_type == "answer":
                response_messages.append(event_content)
                for char in event_content:
                    time.sleep(0.005)
                    yield char

    # 将流式输出写入字符串收集，不直接显示
    for char in capture_answer_events():
        pass  # 收集但不显示，等待头像出现
    final_response = "".join(response_messages)

    # 第二阶段：思考完成，显示 AI 头像和回答
    # 先清空进度状态（可选）
    if error_detected:
        progress_status.update(label="当前模型服务不可用", state="error", expanded=True)
    elif str(final_response).strip():
        progress_status.update(label="✅ 分析完成", state="complete", expanded=False)
    else:
        progress_status.update(label="分析未生成有效结果", state="error", expanded=True)
    
    # 显示带头像的 chat_message
    with st.chat_message("assistant"):
        st.write(str(final_response).strip() if final_response else "当前这次分析没有成功生成结果。")

    return {
        "final_response": str(final_response).strip(),
        "artifacts": artifacts,
        "error_detected": error_detected,
    }


def _run_card_evaluation_simple(finance_agent: FinanceReactAgent, card_instance_id: str) -> dict:
    """
    执行知识卡片评估流程的简化版本。
    
    修复说明：
    - 思考时隐藏 AI 头像，只显示进度状态
    - 回答生成后再显示带头像的 chat_message
    """
    # 第一阶段：显示思考进度，AI 头像隐藏
    progress_status = st.status("📋 正在检查卡片评估窗口...", expanded=True)
    progress_status.write("🔄 正在分析卡片数据...")
    
    response_messages = []
    evaluation_result = None
    error_detected = False
    
    # 使用局部函数来捕获变量
    def capture_events_and_update_progress():
        nonlocal evaluation_result
        nonlocal error_detected
        
        for event in finance_agent.execute_card_evaluation_stream(card_instance_id=card_instance_id):
            event_type = event.get("type")
            event_content = event.get("content", "")

            if event_type == "status":
                progress_status.write(event_content)
                continue

            if event_type == "error":
                error_detected = True
                progress_status.write(event_content)
                continue

            if event_type == "result":
                evaluation_result = event_content
                continue

            if event_type == "answer":
                response_messages.append(event_content)
                for char in event_content:
                    time.sleep(0.005)
                    yield char

    # 收集所有回答内容，不直接显示
    for char in capture_events_and_update_progress():
        pass
    final_response = "".join(response_messages).strip()

    # 第二阶段：评估完成，显示 AI 头像和回答
    # 根据结果更新最终状态
    if error_detected:
        progress_status.update(label="❌ 卡片评估暂时失败", state="error", expanded=True)
    elif final_response:
        if evaluation_result:
            eval_result = evaluation_result.get("evaluation_result", "")
            if eval_result == "completed":
                progress_status.update(label="✅ 卡片评估完成 - 已达标！", state="complete", expanded=False)
            elif eval_result == "improved":
                progress_status.update(label="📈 卡片评估完成 - 有改善！", state="complete", expanded=False)
            elif eval_result == "not_improved":
                progress_status.update(label="📊 卡片评估完成 - 继续观察", state="complete", expanded=False)
            else:
                progress_status.update(label="✅ 卡片评估完成", state="complete", expanded=False)
        else:
            progress_status.update(label="✅ 卡片评估完成", state="complete", expanded=False)
    else:
        progress_status.update(label="⚠️ 卡片评估未生成有效结果", state="error", expanded=True)

    # 显示带头像的 chat_message
    with st.chat_message("assistant"):
        st.write(final_response if final_response else "当前这次卡片评估没有成功生成结果。")

    return {
        "final_response": final_response,
        "evaluation_result": evaluation_result,
        "error_detected": error_detected,
    }


def _handle_card_action(
    selected_card: dict,
    action_type: str,
    source_query: str,
    source_conversation_id: str,
    source_time_label: str,
):
    """
    接收页面按钮动作，并把卡片状态写入本地状态文件。
    """
    user_id = get_current_user_id()
    state_manager = CardStateManager(user_id)
    card_instance = state_manager.record_card_action(
        card_payload=selected_card,
        user_action=action_type,
        source_conversation_id=source_conversation_id,
        source_query=source_query,
        activated_by_time_label=source_time_label,
        eval_cycle_days=int(selected_card.get("recommended_eval_days", 7) or 7),
    )

    if action_type == "accepted":
        flash_type = "success"
        flash_message = f"已加入学习计划，下一次可评估时间：{card_instance.get('next_evaluation_date', '待生成')}。"
    elif action_type == "remind_later":
        flash_type = "info"
        flash_message = "已为你稍后保留这张卡片，当前先不进入 active 评估。"
    else:
        flash_type = "info"
        flash_message = "已记录你先看看内容的选择，这张卡片会进入历史记录。"

    st.session_state["finance_flash_message"] = {
        "type": flash_type,
        "message": flash_message,
    }


def _handle_card_evaluation_check(conv_manager: ConversationManager) -> dict:
    """
    响应侧边栏的“卡片评估检查”按钮。
    """
    user_id = get_current_user_id()
    state_manager = CardStateManager(user_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    due_cards = state_manager.get_due_evaluation_cards(reference_date=today_str)

    if not due_cards:
        return {
            "status": "none",
            "message": "当前没有到期可评估的知识卡片。",
        }

    selected_due_card = due_cards[0]
    new_conversation_id = conv_manager.create_new_conversation_with_title(
        title=f"卡片评估检查｜{selected_due_card.get('card_title', '未命名卡片')}"
    )

    st.session_state["finance_messages"] = []
    st.session_state["finance_current_conversation_id"] = new_conversation_id
    st.session_state["finance_editing_title"] = False
    st.session_state["finance_input_draft"] = ""
    st.session_state["finance_pending_card_evaluation"] = {
        "card_instance_id": selected_due_card.get("card_instance_id"),
        "trigger_message": f"请帮我检查知识卡片《{selected_due_card.get('card_title', '未命名卡片')}》现在是否达到评估条件。",
    }
    return {"status": "scheduled"}


def _update_card_state_after_evaluation(card_instance_id: str, evaluation_result: dict | None):
    """
    根据评估链的结果更新本地卡片状态。
    """
    if not evaluation_result:
        return

    user_id = get_current_user_id()
    state_manager = CardStateManager(user_id)
    suggested_days = max(int(evaluation_result.get("suggested_next_eval_days", 7) or 7), 1)
    next_evaluation_date = (datetime.now().date() + timedelta(days=suggested_days)).strftime("%Y-%m-%d")

    next_action = str(evaluation_result.get("next_action", "continue_tracking"))
    if next_action == "complete_card" or evaluation_result.get("evaluation_result") == "completed":
        state_manager.mark_card_completed(card_instance_id, evaluation_result)
        return

    if next_action == "snooze_card":
        state_manager.snooze_card(card_instance_id, next_evaluation_date, evaluation_result)
        return

    state_manager.update_next_evaluation(card_instance_id, next_evaluation_date, evaluation_result)


def _render_card_recommendation_block(card_recommendation_result: dict, message_index: int):
    """
    渲染 assistant 消息下方的知识卡片推荐区。
    使用 Streamlit 原生组件模拟卡片质感，增强视觉层次。
    
    支持推荐已在学习计划中的卡片：
    - 仍在推荐列表中（只是降低优先级）
    - 但不显示"加入学习计划"按钮
    - 显示当前追踪状态和下次评估时间
    """
    selected_card = card_recommendation_result.get("selected_card") or {}
    if not selected_card:
        return

    user_id = get_current_user_id()
    state_manager = CardStateManager(user_id)
    source_conversation_id = str(
        card_recommendation_result.get("source_conversation_id")
        or st.session_state.get("finance_current_conversation_id")
        or ""
    )
    
    # 从候选结果中获取是否已在学习计划中的标记
    is_already_tracked = card_recommendation_result.get("is_already_tracked", False)
    tracked_instance = card_recommendation_result.get("tracked_instance")
    
    # 如果候选结果中没有追踪信息，则通过查询获取（兼容旧逻辑）
    if not is_already_tracked:
        existing_instance = state_manager.find_existing_card_instance(
            card_id=selected_card.get("card_id", ""),
            source_conversation_id=source_conversation_id,
        )
        if existing_instance and existing_instance.get("status") in {"active", "snoozed"}:
            is_already_tracked = True
            tracked_instance = {
                "card_instance_id": existing_instance.get("card_instance_id"),
                "status": existing_instance.get("status"),
                "next_evaluation_date": existing_instance.get("next_evaluation_date"),
                "eval_cycle_days": existing_instance.get("eval_cycle_days"),
                "user_action": existing_instance.get("user_action"),
            }
    elif tracked_instance is None:
        # 有标记但没有追踪实例信息，需要查询
        existing_instance = state_manager.find_existing_card_instance(
            card_id=selected_card.get("card_id", ""),
            source_conversation_id=source_conversation_id,
        )
        if existing_instance:
            tracked_instance = {
                "card_instance_id": existing_instance.get("card_instance_id"),
                "status": existing_instance.get("status"),
                "next_evaluation_date": existing_instance.get("next_evaluation_date"),
                "eval_cycle_days": existing_instance.get("eval_cycle_days"),
                "user_action": existing_instance.get("user_action"),
            }

    # 使用容器模拟卡片边框和背景，增强视觉层次感
    card_container = st.container(border=True)
    
    with card_container:
        # 卡片标题区
        st.markdown("##### 📚 知识卡片推荐")
        
        # 标签行
        tags = selected_card.get("tags", [])
        if tags:
            st.caption(" ".join(f"`#{tag}`" for tag in tags))
        
        # 标题
        st.markdown(f"**{selected_card.get('title', '未命名卡片')}**")
        
        # 如果已在学习计划中，显示追踪状态提示
        if is_already_tracked and tracked_instance:
            status = tracked_instance.get("status", "active")
            status_emoji = "🟢" if status == "active" else "🟡"
            status_text = "正在学习" if status == "active" else "稍后提醒"
            st.caption(f"{status_emoji} 当前状态：**{status_text}**")
        
        # 分隔线
        st.divider()
        
        # 推荐理由区
        if card_recommendation_result.get("selection_reason"):
            with st.container(border=False):
                st.markdown("💡 **推荐理由**")
                st.caption(card_recommendation_result['selection_reason'])
        
        # 做什么 - 核心行动区
        st.markdown("🎯 **做什么**")
        st.info(selected_card.get('doing_text', '暂无'))
        
        # 为什么 - 解释区
        st.markdown("💡 **为什么**")
        st.write(selected_card.get('why_text', '暂无'))
        
        # 专业名词和权威来源（可折叠）
        professional_term = str(selected_card.get("professional_term", "")).strip()
        authority_source = str(selected_card.get("authority_source", "")).strip()
        
        if professional_term or authority_source:
            with st.expander("📖 知识扩展", expanded=False):
                if professional_term:
                    st.markdown(f"**专业名词**：`{professional_term}`")
                if authority_source:
                    st.caption(f"**来源**：{authority_source}")
        
        st.divider()
        
        # 如果已在学习计划中，显示追踪状态和操作提示
        if is_already_tracked and tracked_instance:
            status = tracked_instance.get("status", "active")
            next_eval_date = tracked_instance.get("next_evaluation_date")
            card_instance_id = tracked_instance.get("card_instance_id")
            
            if next_eval_date:
                st.success(f"✅ 这张卡片已经在你的学习计划中。下一次可评估时间：{next_eval_date}")
            else:
                st.success("✅ 这张卡片已经在你的学习计划中")
            
            # 显示"为什么这张卡片仍然值得关注"的提示
            if card_recommendation_result.get("selection_reason"):
                with st.expander("💡 为什么这张卡片仍然值得关注？"):
                    st.caption(card_recommendation_result.get("selection_reason"))
            
            # 提示用户去侧边栏评估
            st.caption("💡 你可以点击侧边栏的「📋 卡片评估检查」来评估这张卡片")
            
            # 仍然提供"先看看内容"选项（不改变原学习计划）
            st.markdown("**其他操作**")
            if st.button("👀 先看看内容", key=f"finance_card_view_{message_index}_{selected_card.get('card_id', '')}", use_container_width=True):
                _handle_card_action(
                    selected_card=selected_card,
                    action_type="view_only",
                    source_query=card_recommendation_result.get("source_query", ""),
                    source_conversation_id=source_conversation_id,
                    source_time_label=card_recommendation_result.get("source_time_label", "全部历史数据"),
                )
                st.rerun()
            return
        
        # 评估周期提示
        eval_days = selected_card.get("recommended_eval_days", 7) or 7
        st.caption(f"⏰ 推荐评估周期：{eval_days} 天")
        
        # 操作按钮区
        st.markdown("**请选择**")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("✅ 加入学习计划", key=f"finance_card_accept_{message_index}_{selected_card.get('card_id', '')}", use_container_width=True, type="primary"):
                _handle_card_action(
                    selected_card=selected_card,
                    action_type="accepted",
                    source_query=card_recommendation_result.get("source_query", ""),
                    source_conversation_id=source_conversation_id,
                    source_time_label=card_recommendation_result.get("source_time_label", "全部历史数据"),
                )
                st.rerun()

        with action_col2:
            if st.button("⏰ 稍后提醒我", key=f"finance_card_later_{message_index}_{selected_card.get('card_id', '')}", use_container_width=True):
                _handle_card_action(
                    selected_card=selected_card,
                    action_type="remind_later",
                    source_query=card_recommendation_result.get("source_query", ""),
                    source_conversation_id=source_conversation_id,
                    source_time_label=card_recommendation_result.get("source_time_label", "全部历史数据"),
                )
                st.rerun()

        with action_col3:
            if st.button("👀 先看看内容", key=f"finance_card_view_{message_index}_{selected_card.get('card_id', '')}", use_container_width=True):
                _handle_card_action(
                    selected_card=selected_card,
                    action_type="view_only",
                    source_query=card_recommendation_result.get("source_query", ""),
                    source_conversation_id=source_conversation_id,
                    source_time_label=card_recommendation_result.get("source_time_label", "全部历史数据"),
                )
                st.rerun()


def _render_finance_message(message: dict, message_index: int):
    """
    渲染财商聊天消息，并在 assistant 消息下方补充知识卡片区块。
    """
    role = message.get("role", "assistant")
    with st.chat_message(role):
        st.write(message.get("content", ""))
        if role == "assistant" and message.get("card_recommendation"):
            _render_card_recommendation_block(message["card_recommendation"], message_index)


def _save_finance_conversation(conv_manager: ConversationManager) -> str | None:
    """
    保存当前财商助手对话。
    """
    if not st.session_state["finance_messages"]:
        return None

    current_conv_id = st.session_state["finance_current_conversation_id"]
    if current_conv_id is None:
        conversation_id = conv_manager.save_current_conversation(
            st.session_state["finance_messages"],
            conversation_id=None,
        )
        st.session_state["finance_current_conversation_id"] = conversation_id
        return conversation_id
    else:
        conv_manager.save_current_conversation(
            st.session_state["finance_messages"],
            conversation_id=current_conv_id,
        )
        return current_conv_id


def _render_profile_initialization_questionnaire():
    """
    渲染用户画像初始化问卷。
    在用户首次使用时引导完成设置。
    """
    st.markdown("### 👋 欢迎使用 AI 财商助手")
    st.info("""
    在开始之前，让我先了解一下你，这样可以为你提供更贴合你情况的消费建议和分析。
    这只需要几分钟时间，后续随时可以在「⚙️ 个性化设置」中修改。
    """)
    
    with st.form("profile_initialization_form"):
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
        
        submitted = st.form_submit_button("✨ 完成设置，开始使用", type="primary", use_container_width=True)
        
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
            
            # 更新session_state
            st.session_state["profile_initialized"] = True
            
            st.success("✅ 太好了！我已经了解你了，现在可以开始使用财商助手了！")
            st.rerun()


def show_ai_finance_page():
    """
    AI 财商助手页面主函数。
    """
    _init_ai_finance_state()

    user_id = get_current_user_id()
    finance_agent = st.session_state["finance_agent"]
    conv_manager = st.session_state["finance_conversation_manager"]
    
    # 检查用户画像是否已初始化
    profile_manager = UserProfileManager(user_id)
    if not profile_manager.is_initialized():
        # 尚未完成初始化问卷，显示问卷
        _render_profile_initialization_questionnaire()
        return

    _render_finance_sidebar(conv_manager)

    st.title("🤖 AI 财商助手")
    st.caption("你可以直接问消费概览、问题识别、预算执行情况，也可以在当前对话里继续追问。")

    flash_message = st.session_state.get("finance_flash_message")
    if flash_message:
        if flash_message.get("type") == "success":
            st.success(flash_message.get("message", ""))
        elif flash_message.get("type") == "warning":
            st.warning(flash_message.get("message", ""))
        else:
            st.info(flash_message.get("message", ""))
        st.session_state["finance_flash_message"] = None

    _render_example_buttons()
    st.markdown("---")

    # 渲染当前对话消息，让财商助手真正以聊天方式工作。
    for index, message in enumerate(st.session_state["finance_messages"]):
        _render_finance_message(message, index)

    pending_card_evaluation = st.session_state.get("finance_pending_card_evaluation")
    if pending_card_evaluation:
        synthetic_user_message = pending_card_evaluation.get("trigger_message", "请检查这张知识卡片是否到期可评估。")
        st.chat_message("user").write(synthetic_user_message)

        # 使用简化版本，避免头像随思考过程移动
        evaluation_execution = _run_card_evaluation_simple(
            finance_agent=finance_agent,
            card_instance_id=str(pending_card_evaluation.get("card_instance_id", "")),
        )

        final_response = evaluation_execution.get("final_response") or "当前这次卡片评估没有成功生成结果。"
        st.session_state["finance_messages"].append({"role": "user", "content": synthetic_user_message})
        st.session_state["finance_messages"].append({
            "role": "assistant",
            "content": final_response,
            "card_evaluation_result": evaluation_execution.get("evaluation_result"),
        })

        _update_card_state_after_evaluation(
            card_instance_id=str(pending_card_evaluation.get("card_instance_id", "")),
            evaluation_result=evaluation_execution.get("evaluation_result"),
        )
        _save_finance_conversation(conv_manager)
        st.session_state["finance_pending_card_evaluation"] = None
        st.rerun()
        return

    prompt = st.chat_input(
        "告诉 AI 你想分析什么，例如：帮我看看上个月我的消费情况 / 那奶茶占多少？",
        key="finance_input_draft"
    )

    normalized_query = (prompt or "").strip()
    if not normalized_query:
        return

    # 先取“发送前历史”，避免把当前用户问题重复传入 agent。
    history_before_current_turn = list(st.session_state["finance_messages"])

    # 页面上即时展示用户本轮问题。
    st.chat_message("user").write(normalized_query)

    # 执行财商分析（头像在函数内部处理：思考时隐藏，完成后显示）
    execution_result = _run_finance_agent_with_visual_steps(
        finance_agent=finance_agent,
        normalized_query=normalized_query,
        history_before_current_turn=history_before_current_turn,
        runtime_context={
            "user_id": user_id,
            "conversation_id": st.session_state["finance_current_conversation_id"],
            "analysis_mode": "finance_assistant",
            "agent_scene": "finance_assistant",
            "report": False,
        },
    )

    final_response = str(execution_result.get("final_response") or "").strip()
    artifacts = execution_result.get("artifacts", {})

    if not final_response:
        final_response = "当前这次分析没有成功生成结果。你可以换个更具体的问题再试一次。"

    card_recommendation_result = None
    evidence_pack_json = artifacts.get("build_finance_evidence_pack")
    if evidence_pack_json:
        # 为卡片推荐链补一个可见进度反馈，避免用户在这一步"无感等待"。
        # 步骤1：显示正在分析数据
        card_progress_status = st.status("📚 正在根据本次分析结果为你推荐知识卡片...", expanded=True)
        try:
            # 步骤2：显示正在筛选候选
            card_progress_status.write("🔍 正在分析你的消费数据，筛选相关卡片...")
            
            card_recommendation_result = finance_agent.execute_card_recommendation(
                query=normalized_query,
                evidence_pack_json=evidence_pack_json,
                analysis_summary=final_response,
                history=history_before_current_turn,
                runtime_context={
                    "user_id": user_id,
                    "conversation_id": st.session_state["finance_current_conversation_id"],
                },
            )
            
            # 步骤3：根据结果更新状态
            if card_recommendation_result and card_recommendation_result.get("should_recommend"):
                selected_card = card_recommendation_result.get("selected_card") or {}
                card_title = selected_card.get("title", "未命名卡片")
                card_progress_status.write(f"✅ 已找到适合你的卡片：《{card_title}》")
                card_progress_status.update(label="📚 知识卡片推荐完成", state="complete", expanded=False)
            else:
                card_progress_status.write("💡 根据你的情况，本次暂不推荐新卡片")
                card_progress_status.update(label="本轮未推荐新的知识卡片", state="complete", expanded=False)
        except Exception as e:
            card_recommendation_result = None
            card_progress_status.write(f"⚠️ 卡片推荐遇到问题：{str(e)}")
            card_progress_status.update(label="知识卡片推荐流程暂时失败", state="error", expanded=True)

    assistant_message = {"role": "assistant", "content": final_response}
    if card_recommendation_result and card_recommendation_result.get("should_recommend"):
        source_time_label = "全部历史数据"
        try:
            parsed_evidence_pack = cast(dict[str, Any], json.loads(evidence_pack_json))
            source_time_label = str(parsed_evidence_pack.get("task_meta", {}).get("time_label", source_time_label))
        except Exception:
            pass

        assistant_message["card_recommendation"] = {
            **card_recommendation_result,
            "source_query": normalized_query,
            "source_time_label": source_time_label,
            "source_conversation_id": st.session_state.get("finance_current_conversation_id"),
        }

    # 当前轮次结束后，再统一把 user / assistant 消息写回历史。
    st.session_state["finance_messages"].append({"role": "user", "content": normalized_query})
    st.session_state["finance_messages"].append(assistant_message)


    # 把对话落本地，支持后续追问、刷新恢复和历史切换。
    conversation_id = _save_finance_conversation(conv_manager)
    if assistant_message.get("card_recommendation"):
        assistant_message["card_recommendation"]["source_conversation_id"] = conversation_id
        _save_finance_conversation(conv_manager)

    # ==================== Phase 4.5 扩展：财商分析完成后添加积分奖励 ====================
    # 判断本次是否为真正的数据分析（而非轻量问答）
    is_data_analysis = bool(evidence_pack_json)
    if is_data_analysis:
        try:
            from ..utils.points_manager import PointsManager
            points_manager = PointsManager(user_id)
            points_result = points_manager.add_points(
                action="finance_analysis",
                description=f"财商分析奖励 - {normalized_query[:30]}..."
            )
            points_earned = points_result.get("points_earned", 0)
            current_balance = points_result.get("balance_after", 0)
            if points_earned > 0:
                st.session_state["finance_flash_message"] = {
                    "type": "success",
                    "message": f"🎁 完成财商分析奖励：+{points_earned} 积分！当前余额：{current_balance} 分",
                }
        except Exception as e:
            # 积分添加失败不影响主流程
            import logging
            logging.warning(f"[show_ai_finance_page]添加财商分析积分奖励失败: {str(e)}")

    st.session_state["finance_should_clear_input"] = True
    st.rerun()


