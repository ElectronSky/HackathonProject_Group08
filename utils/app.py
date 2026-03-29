#  streamlit run app.py

#   streamlit run HACKATHON_AI_standard\hackathon_project\app.py
# streamlit run app.py

# Disable Chroma telemetry BEFORE any imports to prevent OpenTelemetry initialization errors
import os
import time
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["OTEL_SDK_DISABLED"] = "True"


import streamlit as st
from typing import Any, cast
from agent.react_agent import ReactAgent
from agent.finance_react_agent import FinanceReactAgent
from agent.tools.agent_tools import set_current_user
from utils.conversation_manager import ConversationManager

st.set_page_config(
    page_title="智能记账助手",
    page_icon="💰",
    layout="wide"
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# 创建一个ReactAgent对象并初始化存在ss防止重复调用
    if "agent" not in st.session_state:
        st.session_state["agent"] = None

if "message" not in st.session_state:
    st.session_state["message"] = []

    # 当前对话ID
    if "current_conversation_id" not in st.session_state:
        st.session_state["current_conversation_id"] = None

    # 对话管理器
    if "conversation_manager" not in st.session_state:
        st.session_state["conversation_manager"] = None

    # 当前对话标题编辑状态
    if "editing_title" not in st.session_state:
        st.session_state["editing_title"] = False

if "budget_settings_enabled" not in st.session_state:
    st.session_state["budget_settings_enabled"] = False

# 财商助手页使用独立状态，避免和记账页串台。
if "finance_agent" not in st.session_state:
    st.session_state["finance_agent"] = None

if "finance_messages" not in st.session_state:
    st.session_state["finance_messages"] = []

if "finance_current_conversation_id" not in st.session_state:
    st.session_state["finance_current_conversation_id"] = None

if "finance_conversation_manager" not in st.session_state:
    st.session_state["finance_conversation_manager"] = None

if "finance_editing_title" not in st.session_state:
    st.session_state["finance_editing_title"] = False

if "finance_input_draft" not in st.session_state:
    st.session_state["finance_input_draft"] = ""


def show_login_page():
    """登录/注册页面"""
    st.title("🔐 智能记账助手")
    tab1, tab2 = st.tabs(["登录", "注册"])

    #deleted password and authentication
    with tab1:
        user_id = st.text_input("用户名", key="login_username")
        if st.button("登录"):
            # 设置全局用户 ID
            set_current_user(user_id)
            
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user_id
            st.session_state["agent"] = ReactAgent()  # 不再需要传入 user_id
            st.session_state["finance_agent"] = FinanceReactAgent()
            
            # 初始化记账页和财商助手页各自独立的对话管理器。
            st.session_state["conversation_manager"] = ConversationManager(
                st.session_state["user_id"],
                conversation_type="accounting"
            )
            st.session_state["finance_conversation_manager"] = ConversationManager(
                st.session_state["user_id"],
                conversation_type="finance"
            )
            st.success("登录成功！")
            st.rerun()

    with tab2:
        pass

def show_main_app():
    """主应用页面"""
    with st.sidebar:
        st.write(f"👤 欢迎，{st.session_state['user_id']}")
        if st.button("退出登录"):
            # 清空全局用户 ID
            set_current_user(None)
            
            st.session_state["logged_in"] = False
            st.session_state["user_id"] = None
            st.session_state["agent"] = None
            st.session_state["finance_agent"] = None
            st.session_state["conversation_manager"] = None
            st.session_state["finance_conversation_manager"] = None
            st.session_state["message"] = []
            st.session_state["current_conversation_id"] = None
            st.session_state["editing_title"] = False
            st.session_state["finance_messages"] = []
            st.session_state["finance_current_conversation_id"] = None
            st.session_state["finance_editing_title"] = False
            st.session_state["finance_input_draft"] = ""
            st.rerun()

        page = st.radio(
            "导航",
            ["📝 智能记账", "📒 我的账本", "💰 预算管理", "💎 储蓄账户", "📚 知识卡片", "🤖 ai财商助手", "🎁 积分商城", "⚙️ 设置"],
            index=0
        )

    if page == "📝 智能记账":
        show_accounting_page()
    elif page == "📒 我的账本":
        from pages._ledger_page import show_ledger_page
        show_ledger_page()
    elif page == "💰 预算管理":
        from pages._budget_page import show_budget_page
        show_budget_page()
    elif page == "💎 储蓄账户":
        from pages._accounts_page import show_accounts_page
        show_accounts_page()
    elif page == "📚 知识卡片":
        from pages._knowledge_cards_page import show_knowledge_cards_page
        show_knowledge_cards_page()
    elif page == "🤖 ai财商助手":
        from pages._ai_finance_page import show_ai_finance_page
        show_ai_finance_page()
    elif page == "🎁 积分商城":
        from pages._points_mall_page import show_points_mall_page
        show_points_mall_page()
    elif page == "⚙️ 设置":
        from pages._settings_page import show_settings_page
        show_settings_page()


def show_accounting_page():
    """
    智能记账页面。
    
    与财商助手和优惠券推荐页面对齐：使用 st.status() 展示工具调用过程。
    """
    st.title("📝 智能记账")

    # 侧边栏 - 对话管理功能（仅限记账页面）
    with st.sidebar:
        st.markdown("---")
        st.subheader("对话管理")

        # 新对话按钮
        if st.button("🆕 新对话", key="new_conversation", use_container_width=True):
            st.session_state["message"] = []
            st.session_state["current_conversation_id"] = None
            st.rerun()

        # 当前对话标题显示/编辑
        current_conv_id = st.session_state["current_conversation_id"]
        conv_manager = st.session_state["conversation_manager"]
        
        if current_conv_id:
            conversations = conv_manager.get_user_conversations()
            current_conv = next((c for c in conversations if c["id"] == current_conv_id), None)
            if current_conv:
                title = current_conv["title"]
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.session_state["editing_title"]:
                        new_title = st.text_input("", value=title, label_visibility="collapsed", key="title_input")
                    else:
                        st.write(f"**{title}**")
                
                with col2:
                    if st.session_state["editing_title"]:
                        if st.button("✅", key="save_title", use_container_width=True):
                            # 保存对话标题
                            conv_manager.save_current_conversation(st.session_state["message"], new_title, st.session_state["current_conversation_id"])
                            st.session_state["editing_title"] = False
                            st.rerun()
                    else:
                        if st.button("✏️", key="edit_title", use_container_width=True):
                            st.session_state["editing_title"] = True
                            st.rerun()
        else:
            st.write("**新对话**")

        # 历史对话列表
        st.markdown("### 📜 历史对话")
        conversations = conv_manager.get_user_conversations()
        
        for conv in conversations:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                conv_time = conv["updated_at"].split("T")[0]
                if st.button(f"💬 {conv['title']} ({conv_time})", key=f"load_{conv['id']}", use_container_width=True):
                    messages = conv_manager.load_conversation(conv["id"])
                    if messages is not None:
                        st.session_state["message"] = messages
                        st.session_state["current_conversation_id"] = conv["id"]
                        st.session_state["editing_title"] = False
                        st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{conv['id']}", use_container_width=True):
                    if conv_manager.delete_conversation(conv["id"]):
                        # 如果删除的是当前对话，清空消息
                        if st.session_state["current_conversation_id"] == conv["id"]:
                            st.session_state["message"] = []
                            st.session_state["current_conversation_id"] = None
                        st.rerun()

    # 保存当前对话
    if len(st.session_state["message"]) > 0:
        if current_conv_id is None:
            # 创建新对话
            conversation_id = conv_manager.save_current_conversation(st.session_state["message"], conversation_id=None)
            st.session_state["current_conversation_id"] = conversation_id
        else:
            # 更新现有对话
            conv_manager.save_current_conversation(st.session_state["message"], conversation_id=current_conv_id)
    
    # 书写当前消息列表
    for message in st.session_state["message"]:
        st.chat_message(message["role"]).write(message["content"])

    # 输入区域
    user_input = st.text_area(
        "描述你的消费",
        placeholder="例：今天中午在蜜雪冰城买了杯6块钱的奶茶",
        height=100
    )

    if st.button("🤖 智能识别", type="primary"):
        if not user_input.strip():
            st.warning("请输入消费描述")
            return

        st.session_state["message"].append({"role": "user", "content": user_input})

        # 使用与财商助手和优惠券推荐页面对齐的展示方式：st.status() + write_stream()
        progress_status = st.status("🧠 AI 正在理解你的记账意图...", expanded=True)
        answer_placeholder = st.empty()
        
        response_messages = []
        error_detected = False
        
        def capture_events():
            """
            捕获 agent 事件流，与财商助手页面展示方式对齐。
            """
            nonlocal error_detected
            
            for event in st.session_state["agent"].execute_stream_with_events(
                user_input,
                st.session_state["message"]
            ):
                event_type = event.get("type")
                event_content = event.get("content", "")
                
                if event_type == "status":
                    # 工具调用状态，展示在 st.status 中
                    progress_status.write(event_content)
                    continue
                
                if event_type == "error":
                    error_detected = True
                    progress_status.write(event_content)
                    continue
                
                if event_type == "answer":
                    response_messages.append(event_content)
                    # 流式输出：逐字符输出
                    for char in event_content:
                        time.sleep(0.005)
                        yield char
        
        # 在 assistant 消息框中流式输出
        with st.chat_message("assistant"):
            answer_placeholder.write_stream(capture_events())
        
        final_response = "".join(response_messages)
        
        # 根据结果更新状态
        if error_detected:
            progress_status.update(label="❌ 记账遇到问题", state="error", expanded=True)
        elif final_response.strip():
            progress_status.update(label="✅ 记账完成", state="complete", expanded=False)
        else:
            progress_status.update(label="⚠️ 未生成有效结果", state="error", expanded=True)
        
        # 把最终回复加入消息历史
        st.session_state["message"].append({"role": "assistant", "content": final_response})
        
        # 保存到本地
        conv_manager.save_current_conversation(
            st.session_state["message"],
            conversation_id=st.session_state["current_conversation_id"]
        )
        
        st.rerun()


if __name__ == "__main__":
    if not st.session_state["logged_in"]:
        show_login_page()
    else:
        show_main_app()
