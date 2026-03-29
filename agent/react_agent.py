#alt+shift+enter 自动的导入


from langchain.agents import create_agent
from typing import Any, Optional, cast

try:
    from .middleware import monitor_tool, log_before_model, report_prompt_switch
    from .tools.agent_tools import rag_summarize, get_categories, record_expense, get_current_time, record_income, adjust_account_balance
    from ..model.factory import chat_model
    from ..utils.prompt_loader import load_system_prompt
    from ..utils.model_error_helper import normalize_model_error
except ImportError:
    from importlib import import_module

    middleware_module = import_module("agent.middleware")
    monitor_tool = middleware_module.monitor_tool
    log_before_model = middleware_module.log_before_model
    report_prompt_switch = middleware_module.report_prompt_switch

    tools_module = import_module("agent.tools.agent_tools")
    rag_summarize = tools_module.rag_summarize
    get_categories = tools_module.get_categories
    record_expense = tools_module.record_expense
    get_current_time = tools_module.get_current_time
    record_income = tools_module.record_income
    adjust_account_balance = tools_module.adjust_account_balance

    chat_model = import_module("model.factory").chat_model
    load_system_prompt = import_module("utils.prompt_loader").load_system_prompt
    normalize_model_error = import_module("utils.model_error_helper").normalize_model_error


class ReactAgent:

    def __init__(self):
        """
        初始化 ReactAgent
        """
        self.agent = create_agent(
            #这里不可以使用 chat_model() 因为会报错
            model = chat_model,
            system_prompt = load_system_prompt(),
            tools = [rag_summarize, get_categories, record_expense, get_current_time, record_income, adjust_account_balance],
            middleware = [monitor_tool, log_before_model, report_prompt_switch],
        )

    @staticmethod
    def _build_tool_status_message(tool_name: str, tool_args: dict | None = None, completed: bool = False, tool_result: str = None) -> str:
        """
        为页面侧的"过程展示区"生成更友好的工具调用状态文案。
        """
        tool_args = tool_args or {}
        
        if completed:
            if tool_name == "get_current_time":
                if tool_result:
                    return f"[完成] 当前时间：{tool_result.strip()}"
                return "[完成] 已获取当前时间"
            
            if tool_name == "get_categories":
                return "[完成] 已获取支出类别列表"
            
            if tool_name == "record_expense":
                if tool_result:
                    return f"[完成] {tool_result.strip()}"
                amount = tool_args.get("amount", "")
                category = tool_args.get("category", "")
                return f"[完成] 已记录支出：¥{amount} {category}"
            
            if tool_name == "record_income":
                if tool_result:
                    return f"[完成] {tool_result.strip()}"
                amount = tool_args.get("amount", "")
                source = tool_args.get("source", "")
                return f"[完成] 已记录收入：¥{amount} {source}"
            
            if tool_name == "adjust_account_balance":
                if tool_result:
                    return f"[完成] {tool_result.strip()}"
                account_type = tool_args.get("account_type", "")
                change_amount = tool_args.get("change_amount", 0)
                account_name = "储蓄账户" if account_type == "savings" else "流动资金"
                sign = "+" if float(change_amount) > 0 else ""
                return f"[完成] 已调整{account_name}余额：{sign}{change_amount}"
            
            if tool_name == "rag_summarize":
                return "[完成] 已检索财商知识支持"
            
            return f"[完成] {tool_name}"

        # ===== 以下是工具调用前的状态提示（未完成）=====
        
        if tool_name == "get_current_time":
            return "正在获取当前时间..."
        
        if tool_name == "get_categories":
            return "正在获取支出类别列表..."
        
        if tool_name == "record_expense":
            description = tool_args.get("description", "支出记录")
            amount = tool_args.get("amount", "")
            return f"正在记录支出：¥{amount} {description}..."
        
        if tool_name == "record_income":
            source = tool_args.get("source", "收入")
            amount = tool_args.get("amount", "")
            return f"正在记录收入：¥{amount} {source}..."
        
        if tool_name == "adjust_account_balance":
            account_type = tool_args.get("account_type", "")
            change_amount = tool_args.get("change_amount", 0)
            account_name = "储蓄账户" if account_type == "savings" else "流动资金"
            return f"正在调整{account_name}余额..."
        
        if tool_name == "rag_summarize":
            query = tool_args.get("query", "")
            if len(query) > 30:
                query = query[:30] + "..."
            return f"正在检索财商知识：{query}..."

        return f"正在调用：{tool_name}..."

    def execute_stream_with_events(self, query: str, history: list = None):
        """
        执行带事件流的记账分析，与财商助手页面展示方式对齐。
        
        事件类型：
        - status: 给页面展示"当前做到哪一步了"
        - answer: 给页面展示最终回答内容
        - error: 给页面展示错误信息
        
        Args:
            query: 当前用户输入
            history: 对话历史消息列表，默认为空
            
        Returns:
            生成器，产出事件字典
        """
        # 一进入流程，先给页面一个通用启动提示。
        yield {
            "type": "status",
            "stage": "start",
            "content": "正在理解你的记账意图..."
        }

        # 构建完整的输入消息序列
        input_messages = []
        
        # 添加历史消息（如果存在）
        if history:
            input_messages.extend(history)
            
        # 添加当前查询
        input_messages.append({"role": "user", "content": query})
        
        # 为当前agent准备运行时状态
        merged_context = {
            "report": False,
        }
        
        last_emitted_text = ""
        # 使用字典记录每个工具的调用参数
        pending_tool_calls: dict[str, dict] = {}
        tool_call_order: list[str] = []
        
        try:
            for chunk in self.agent.stream(
                cast(Any, {"messages": input_messages}),
                stream_mode="values",
                context=cast(Any, merged_context)
            ):
                latest_message = chunk["messages"][-1]
                latest_message_type = type(latest_message).__name__

                if latest_message_type == "ToolMessage":
                    # 找到对应的工具调用参数
                    if tool_call_order:
                        tool_name = tool_call_order.pop(0)
                        tool_args = pending_tool_calls.pop(tool_name, {})
                        tool_result = getattr(latest_message, "content", None) or ""
                        if isinstance(tool_result, list):
                            tool_result = "".join([str(x) for x in tool_result])
                    else:
                        tool_name = "unknown_tool"
                        tool_args = {}
                        tool_result = getattr(latest_message, "content", None) or ""
                    
                    yield {
                        "type": "status",
                        "stage": "tool_completed",
                        "content": self._build_tool_status_message(
                            tool_name, 
                            tool_args=tool_args, 
                            completed=True,
                            tool_result=str(tool_result) if tool_result else None
                        ),
                    }
                    continue

                if latest_message_type == "HumanMessage":
                    continue

                latest_tool_calls = getattr(latest_message, "tool_calls", None)
                if latest_tool_calls:
                    for tool_call in latest_tool_calls:
                        tool_name = tool_call.get("name", "unknown_tool")
                        tool_args = tool_call.get("args", {})
                        
                        # 保存工具参数以便在工具完成后使用
                        pending_tool_calls[tool_name] = tool_args
                        tool_call_order.append(tool_name)

                        yield {
                            "type": "status",
                            "stage": "tool_call",
                            "content": self._build_tool_status_message(tool_name, tool_args=tool_args, completed=False),
                        }
                    continue

                current_text = getattr(latest_message, "content", "") or ""
                if isinstance(current_text, list):
                    # 处理 content 是列表的情况
                    text_parts = []
                    for item in current_text:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    current_text = "".join(text_parts)
                
                current_text = current_text.strip()
                if not current_text:
                    continue

                # 流式输出：只输出新增内容
                if current_text.startswith(last_emitted_text):
                    delta_text = current_text[len(last_emitted_text):]
                else:
                    delta_text = current_text

                if delta_text:
                    last_emitted_text = current_text
                    yield {
                        "type": "answer",
                        "content": delta_text,
                    }
                    
        except Exception as error:
            normalized_error = normalize_model_error(error)
            yield {
                "type": "error",
                "stage": "model_error",
                "content": normalized_error["status_message"],
            }
            yield {
                "type": "answer",
                "content": normalized_error["user_message"],
            }

    # 流式输出方法，支持对话历史
    def execute_stream(self, query: str, history: list = None):
        """
        执行流式输出，支持对话历史
        
        Args:
            query: 当前用户输入
            history: 对话历史消息列表，默认为空
            
        Returns:
            生成器，产出响应内容
        """
        # 构建完整的输入消息序列
        input_messages = []
        
        # 添加历史消息（如果存在）
        if history:
            input_messages.extend(history)
            
        # 添加当前查询
        input_messages.append({"role": "user", "content": query})
        
        # 创建输入字典
        input_dict = {
            "messages": input_messages
        }
        
        try:
            # 执行agent流
            for chunk in self.agent.stream(
                cast(Any, input_dict),
                stream_mode="values",
                context=cast(Any, {"report": False})
            ):
                latest_message = chunk["messages"][-1]
                if latest_message.content:
                    yield latest_message.content.strip() + "\n"
        except Exception as error:
            normalized_error = normalize_model_error(error)
            yield normalized_error["user_message"] + "\n"


#是可以执行报告+多个任务的，因为react_agent会重复执行execute_stream(), report会重新变为false并获取数据。这些历史数据会存储在运行时context中，所以可以同时得到多次react后的信息库，当决定信息足够是就一口气结合最开始的要求输出出来。结束！！！！！！！！！！！！！！！！！！！！！！！！！！
if __name__ == "__main__":
    agent = ReactAgent()
    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)
