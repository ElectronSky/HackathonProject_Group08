
# monitor_tool 监控工具
# log_before_model 在模型运行前打印日志
# 提问时如果拦截到用户意图要生成报告，就进行提示词切换，

#如果抓取到用户意图，就进行状态注入，往runtime里面塞东西，比如运行时参数里面塞一个标记report=True，然后根据这个参数来判断是否生成报告


#日志
from typing import Callable, Any
#agent
from langchain.agents import AgentState
#中间件工具
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage

from langgraph.runtime import Runtime
from langgraph.types import Command

try:
    from ..utils.logger_handler import logger
except ImportError:
    from utils.logger_handler import logger

try:
    from ..utils.prompt_loader import (
        load_system_prompt,
        load_report_prompt,
        load_finance_agent_prompt,
        load_finance_agent_prompt_with_profile,
        load_finance_report_prompt_with_profile,
        load_card_recommendation_prompt,
        load_card_evaluation_prompt,
    )
except ImportError:
    from utils.prompt_loader import (
        load_system_prompt,
        load_report_prompt,
        load_finance_agent_prompt,
        load_finance_agent_prompt_with_profile,
        load_finance_report_prompt_with_profile,
        load_card_recommendation_prompt,
        load_card_evaluation_prompt,
    )

@wrap_tool_call
def monitor_tool(
        request = ToolCallRequest,
        # 请求数据,callable里面的是函数参数
        handler = Callable[[ToolCallRequest], ToolMessage | Command]

) -> ToolMessage | Command :
    # REQUEST: 请求的数据封装
    # Handler: 模型运行前的处理函数
    #这里写自定义逻辑
    logger.info(f"[tool monitor]执行工具: {request.tool_call['name']}")
    logger.info(f"[tool monitor]参数: {request.tool_call['args']}")

    #其实接下来就是调用result = handler(request)，只是万一中间有个问题要抓取错误，没问题要输出调用成功
    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")



        # 切换提示词的状态注入区
        # 如果用户意图是生成报告，就进行提示词切换 request.tool_call['name']为当前执行的工具名
        if request.tool_call['name'] == 'fill_context_for_report':
            logger.info(f"[tool monitor]fill_context_for_report工具被调用，注入上下文 report=True")
            # 往request.runtime.context里注入key为report，就监控并标记为生成报告状态
            request.runtime.context["report"] = True
            # 同时保留当前 agent 场景，供动态提示词切换时选择正确的报告提示词
            request.runtime.context["agent_scene"] = request.runtime.context.get("agent_scene", "accounting")

        if request.tool_call['name'] == 'fill_context_for_card_recommendation':
            logger.info("[tool monitor]fill_context_for_card_recommendation工具被调用，注入上下文 card_recommendation_mode=True")
            request.runtime.context["card_recommendation_mode"] = True

        if request.tool_call['name'] == 'fill_context_for_card_evaluation':
            logger.info("[tool monitor]fill_context_for_card_evaluation工具被调用，注入上下文 card_evaluation_mode=True")
            request.runtime.context["card_evaluation_mode"] = True








        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败: {e}")
        raise e


#vbs
#自动为 record_expense 添加 user_id 参数
@wrap_tool_call
def inject_user_id(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command]
) -> ToolMessage | Command:
    """
    中间件：自动为 record_expense 工具注入 user_id 参数
    """
    from langgraph.types import Command
    
    if request.tool_call['name'] == "record_expense":
        # 从 context 中获取 user_id
        user_id = request.context.get("user_id") if hasattr(request, 'context') else None
        
        if user_id:
            # 修改工具的入参，添加 user_id
            modified_args = {**request.args, "user_id": user_id}
            request = request.copy(update={"args": modified_args})
    
    return handler(request)


@before_model
def log_before_model(
        state = AgentState, # agent状态数据
        runtime = Runtime # 运行时参数

):
    logger.info(f"[log_before_model]: 即将调用模型，带有{len(state['messages'])}条消息")
    for message in state['messages']:
        if hasattr(message, 'content') and message.content is not None:
            logger.info(f"[log_before_model][{type(message).__name__}]: {str(message.content).strip()}")


    return None



#每一次在生成提示词之前自动调用dynamic_prompt函数
#自己修改提示词并传给大模型
@dynamic_prompt
def report_prompt_switch(request: ModelRequest):

    #获取运行时参数里标记的生成报告状态
    #request.runtime.context.get()如果找不到Report key就返回1true，不然返回默认（找得到）值false
    is_report = request.runtime.context.get("report", False)
    agent_scene = request.runtime.context.get("agent_scene", "accounting")
    is_card_recommendation = request.runtime.context.get("card_recommendation_mode", False)
    is_card_evaluation = request.runtime.context.get("card_evaluation_mode", False)
    
    # 获取当前用户ID，用于注入用户画像上下文
    user_id = request.runtime.context.get("user_id")
    
    # 调试日志：打印获取到的user_id
    logger.info(f"[report_prompt_switch] 获取到user_id: {user_id}")
    logger.info(f"[report_prompt_switch] agent_scene: {agent_scene}, is_report: {is_report}")

    if is_card_recommendation:
        logger.info("[report_prompt_switch]: 模型运行前，将提示词切换为知识卡片推荐提示词")
        return load_card_recommendation_prompt()

    if is_card_evaluation:
        logger.info("[report_prompt_switch]: 模型运行前，将提示词切换为知识卡片评估提示词")
        return load_card_evaluation_prompt()

    if is_report:
        if agent_scene == "finance_assistant":
            logger.info(f"[report_prompt_switch]: 模型运行前，将提示词切换为财商报告提示词")
            # 如果有用户ID，注入用户画像上下文
            if user_id:
                return load_finance_report_prompt_with_profile(user_id)
            return load_finance_report_prompt()

        logger.info(f"[report_prompt_switch]: 模型运行前，将提示词切换为生成报告提示词")
        return load_report_prompt()
    else:
        if agent_scene == "finance_assistant":
            logger.info(f"[report_prompt_switch]: 模型运行前，将提示词切换为财商主提示词")
            # 如果有用户ID，注入用户画像上下文
            if user_id:
                return load_finance_agent_prompt_with_profile(user_id)
            return load_finance_agent_prompt()

        logger.info(f"[report_prompt_switch]: 模型运行前，将提示词切换为系统提示词")
        return load_system_prompt()


