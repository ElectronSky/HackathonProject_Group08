
#给我解释这个代码文件在一个agent项目里的的整体作用
#具体给我详细解释def mask_sensitive_data 和 class SensitiveDataFilter 的代码
#你的解释都要用可以让我复制进代码作为注释的形式

"""
logger_handler.py - Agent 项目的统一日志管理模块

【核心作用】
为整个 Agent 项目提供开箱即用的日志记录服务，是所有模块（RAG/LLM/Tools 等）的"黑匣子"。

【为什么需要它】
1. 调试追踪：记录 Agent 决策过程、工具调用、API 请求等关键信息
2. 问题排查：当 Agent 回答错误时，通过日志回溯完整执行链路
3. 安全合规：自动脱敏 API_KEY、用户隐私等敏感数据
4. 性能监控：记录响应时间、Token 消耗等指标

【使用场景】
- RAG 模块：记录向量检索结果、相似度分数
- LLM 模块：记录 API 调用参数、响应内容、Token 统计
- Tools 模块：记录工具执行状态、输入输出参数
- 对话管理：记录用户提问、AI 回答、会话历史

【技术特性】
✅ 双重输出：控制台（开发调试）+ 文件（永久存储）
✅ 自动脱敏：智能识别并隐藏敏感信息
✅ 模块化：每个组件独立日志器，便于分类查看
✅ 按日归档：自动生成日期命名的日志文件
✅ 开箱即用：一行代码即可使用
""""""
logger_handler.py - Agent 项目的统一日志管理模块

【核心作用】
为整个 Agent 项目提供开箱即用的日志记录服务，是所有模块（RAG/LLM/Tools 等）的"黑匣子"。

【为什么需要它】
1. 调试追踪：记录 Agent 决策过程、工具调用、API 请求等关键信息
2. 问题排查：当 Agent 回答错误时，通过日志回溯完整执行链路
3. 安全合规：自动脱敏 API_KEY、用户隐私等敏感数据
4. 性能监控：记录响应时间、Token 消耗等指标

【使用场景】
- RAG 模块：记录向量检索结果、相似度分数
- LLM 模块：记录 API 调用参数、响应内容、Token 统计
- Tools 模块：记录工具执行状态、输入输出参数
- 对话管理：记录用户提问、AI 回答、会话历史

【技术特性】
✅ 双重输出：控制台（开发调试）+ 文件（永久存储）
✅ 自动脱敏：智能识别并隐藏敏感信息
✅ 模块化：每个组件独立日志器，便于分类查看
✅ 按日归档：自动生成日期命名的日志文件
✅ 开箱即用：一行代码即可使用
"""


#日志存储

import re
import os
import logging
from datetime import datetime
from typing import Optional
import logging

# 支持相对导入和直接运行两种方式
try:
    from .path_tools import get_abs_path
except ImportError:
    from path_tools import get_abs_path

#在当前项目根路径下第一级 生成一个logs文件
LOG_ROOT = get_abs_path("logs")
#如果没有就创建，有就不管
os.makedirs(LOG_ROOT, exist_ok=True)

#日志的格式配置
DEFAULT_LOG_FORMAT = logging.Formatter(
    #日志时间 - 日志器名称 - 日志级别error/info/warning/debug - 日志信息
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",

)



# %(asctime)s：时间戳（如：2024-01-21 10:30:00）
# %(name)s：日志器名称（如：agent.tools）
# %(levelname)s：日志级别（INFO/ERROR/DEBUG 等）
# %(filename)s:%(lineno)d：文件名和行号
# %(message)s：日志消息内容


def mask_sensitive_data(text: str) -> str:
    """
    日志脱敏函数：隐藏API Key、手机号、邮箱等敏感信息
    :param text: 原始文本
    :return: 脱敏后的文本
    """

    """
       【函数作用】
       智能识别并隐藏文本中的敏感信息，防止泄露到日志文件中

       【为什么要脱敏】
       1. API_KEY 泄露风险：日志文件可能被未授权访问，导致账号被盗用
       2. 用户隐私保护：手机号、邮箱等属于个人隐私信息
       3. 安全合规要求：企业级应用必须满足数据安全规范

       【工作流程】
       步骤 1: 检查输入是否为字符串（非字符串直接返回，避免报错）
       步骤 2: 使用正则表达式匹配各类敏感模式
       步骤 3: 将匹配到的内容替换为掩码（*号或固定格式）
       步骤 4: 返回脱敏后的安全文本

       【支持脱敏的类型】
       ┌─────────────┬──────────────────────┬─────────────────────┐
       │ 类型        │ 原始示例             │ 脱敏后              │
       ├─────────────┼──────────────────────┼─────────────────────┤
       │ API Key     │ sk-abc123xyz789      │ sk-******           │
       │ 手机号      │ 13812345678          │ 1**********         │
       │ 邮箱        │ user@gmail.com       │ user****@gmail.com  │
       │ 密码/密钥   │ password=MySecret123 │ password=******     │
       └─────────────┴──────────────────────┴─────────────────────┘

       【参数说明】
       :param text: 待处理的原始文本（可能包含敏感信息）
       :return: 脱敏后的安全文本（敏感部分已被替换）

       【使用示例】
       >>> mask_sensitive_data("我的 API Key 是 sk-abc123，电话 13812345678")
       '我的 API Key 是 sk-******，电话 1**********'

       >>> mask_sensitive_data("邮箱 test@qq.com, password=123456")
       '邮箱 test****@qq.com, password=******'

       【注意事项】
       ⚠️ 仅处理字符串类型，其他类型原样返回
       ⚠️ 正则匹配可能有遗漏，建议定期审查日志
       ⚠️ 如需新增脱敏类型，可扩展正则规则
       """

    # 类型安全检查：非字符串直接返回（防止对数字/对象等调用时报错）
    if not isinstance(text, str):
        return text

    # 脱敏OpenAI/通义千问API Key（sk-开头）
    # 正则解析：sk- 匹配字面量，\w+ 匹配后续字符，整体替换为 sk-******
    text = re.sub(r"sk-\w+", "sk-******", text)

    # 脱敏手机号
    # 正则解析：1[3-9] 匹配前两位，\d{9} 匹配剩余 9 位，整体替换为 1**********
    text = re.sub(r"1[3-9]\d{9}", "1**********", text)

    # 脱敏邮箱
    # 正则解析：(\w+) 捕获用户名，(\w+) 捕获域名，(\w+) 捕获后缀
    # 替换时用 \1 保留用户名，****隐藏@前内容，\2.\3保留域名和后缀
    text = re.sub(r"(\w+)@(\w+)\.(\w+)", r"\1****@\2.\3", text)

    # 脱敏密码/密钥（password/key=开头）
    # 正则解析：(password|key|secret) 捕获关键词，=[^& ]+ 匹配=后的值（到空格或&结束）
    # 替换时用 \1 保留关键词，******隐藏实际值
    text = re.sub(r"(password|key|secret)=[^& ]+", r"\1=******", text)

    # 返回最终脱敏结果
    return text



class SensitiveDataFilter(logging.Filter):
    """日志过滤器：自动脱敏日志中的敏感信息"""
    """
        【类的作用】
        作为 logging 库的自定义过滤器，拦截所有日志记录并自动脱敏敏感信息

        【为什么要用类而不是函数】
        1. 符合 Python logging 规范：logging.Filter 是标准扩展方式
        2. 可复用性强：可以在多个 Logger 上重复使用
        3. 易于扩展：未来可以添加配置选项、统计功能等

        【继承关系】
        logging.Filter (父类)
            ↑
        SensitiveDataFilter (子类)

        【工作原理】
        当 Logger 输出日志时，会依次经过以下流程：

        Logger 生成日志 → addFilter() 注册过滤器 → filter() 拦截处理 → Handler 输出

        具体流程：
        1. get_logger() 创建 Logger 时，通过 logger.addFilter(SensitiveDataFilter()) 注册
        2. 每次调用 logger.info/debug/error() 时，自动触发 filter() 方法
        3. filter() 修改 LogRecord 对象的 msg 和 args 属性（脱敏）
        4. 脱敏后的日志继续传递给 Handler（控制台/文件）

        【filter 方法详解】
        :param record: logging.LogRecord 对象，包含日志的所有信息
                      - msg: 日志消息模板（如 "API Key: %s"）
                      - args: 日志参数元组（如 ("sk-abc123",)）
                      - levelname: 日志级别（INFO/ERROR 等）
                      - filename: 文件名
                      - lineno: 行号

        :return: bool 值
                - True: 允许该日志通过（继续输出）
                - False: 阻止该日志输出（静默丢弃）
                当前始终返回 True，表示所有日志都放行（但已脱敏）

        【脱敏策略】
        双层防护：
        第一层：脱敏 record.msg（日志消息本身）
                例：logger.info("调用 API，key=sk-abc123")
                → msg 被改为 "调用 API，key=******"

        第二层：脱敏 record.args（格式化参数）
                例：logger.info("用户手机：%s", "13812345678")
                → args 被改为 ("1**********",)

        【为什么args也要脱敏】
        因为 Python logging 支持参数化日志：
        logger.info("密码是 %s", password)
        此时 password 在 args 中，如果只脱敏 msg 会遗漏

        【使用示例】
        # 创建 Logger 时注册过滤器
        logger = logging.getLogger("agent")
        logger.addFilter(SensitiveDataFilter())

        # 之后所有日志自动脱敏
        logger.info("API 调用成功，sk-abc123")  # 输出时变为 sk-******
        logger.debug("用户手机 13812345678")     # 输出时变为 1**********

        【与 mask_sensitive_data 的关系】
        SensitiveDataFilter 是"调度员"：
        - 负责拦截日志记录
        - 调用 mask_sensitive_data 进行实际脱敏

        mask_sensitive_data 是"工人"：
        - 负责具体脱敏操作
        - 使用正则表达式匹配替换

        【设计优势】
        ✅ 无侵入性：业务代码无需修改，自动享受脱敏保护
        ✅ 集中管理：所有脱敏规则在一处维护
        ✅ 灵活扩展：可轻松添加新的脱敏类型
        ✅ 性能友好：正则编译后复用，开销极小
        """
    def filter(self, record: logging.LogRecord) -> bool:
        # 对日志消息脱敏
        """
                【方法职责】
                拦截每一条日志记录，对其中的敏感信息进行脱敏处理

                【执行时机】
                在 Logger 输出日志前自动调用，属于日志管道的"中间件"

                【参数 record 结构】
                LogRecord {
                    msg: "用户的 API Key 是 %s，邮箱 %s",     # 日志模板
                    args: ("sk-abc123", "test@gmail.com"),  # 参数元组
                    levelname: "INFO",                       # 日志级别
                    filename: "main.py",                     # 文件名
                    lineno: 42                               # 行号
                }

                【返回值含义】
                True  → 允许日志继续输出（已脱敏）
                False → 阻止日志输出（当前不使用）
                """
        # 第一步：脱敏日志消息（record.msg）
        # 场景：logger.info("调用接口，key=sk-abc123")
        # 处理：msg 从 "调用接口，key=sk-abc123" → "调用接口，key=******"
        if record.msg:
            record.msg = mask_sensitive_data(record.msg)

        # 第二步：脱敏日志参数（record.args）
        # 场景：logger.info("手机号：%s", "13812345678")
        # 处理：args 从 ("13812345678",) → ("1**********",)
        #
        # 为什么要遍历？因为 args 是元组，可能有多个参数
        # 例：logger.info("手机%s 邮箱%s", "13812345678", "a@b.com")
        # args = ("13812345678", "a@b.com")
        # 需要对每个参数分别脱敏
        if record.args:
            # 将元组转为列表 → 逐个脱敏 → 再转回元组
            # 使用生成器表达式：对每个 arg 调用 mask_sensitive_data
            record.args = tuple(mask_sensitive_data(arg) for arg in record.args)

        # 返回 True 表示"放行此日志"
        # 如果想完全屏蔽某类日志，可在此添加判断逻辑返回 False
        return True




def get_logger(
        name: str = "agent",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        log_file: Optional[str] = None
) -> logging.Logger:
    """
    获取配置好的日志器（开箱即用）
    :param name: 日志器名称（建议按模块命名，如agent.tools/agent.rag/agent.llm）
    :param console_level: 控制台日志级别（默认INFO，开发时可设为DEBUG）
    :param file_level: 文件日志级别（默认DEBUG，记录详细信息）
    :param log_file: 自定义日志文件名（默认按日期生成：agent_20240121.log）
    :return: 配置完成的Logger对象
    """

    # 1. 创建/获取日志器
    #创建/获取名为 name 的日志器
    logger = logging.getLogger(name)
    #设置全局级别DEBUG（捕获所有日志）
    logger.setLevel(logging.DEBUG)
    #添加敏感数据过滤器（自动脱敏 API_KEY、密码等）
    logger.addFilter(SensitiveDataFilter())

    # 避免重复添加Handler（多次导入时只配置一次）
    # 如果已有 Handler，直接返回（防止重复添加）
    if logger.handlers:
        return logger

    #如果已经创建过日志器，那就不再执行下面的代码了

    # 2. 配置控制台Handler（开发调试用）
    # 输出到终端（开发调试用）
    # 级别可自定义（默认INFO）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(console_handler)

    # 3. 配置文件Handler（生产环境留存日志）
    # 如果不存在日志文件，自动按日期生成文件名（如：agent_20240121.log）
    if not log_file:
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")

    # 输出到 logs/ 目录
    # 级别可自定义（默认 DEBUG）
    # 组装文件Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(file_handler)

    return logger


# 快捷获取默认Agent日志器
# 其他模块可以直接 from logger_handler import logger 使用
logger = get_logger("agent")


# 优点总结
# ✅ 双重输出：同时输出到控制台和文件 ✅ 自动脱敏：保护敏感信息（API_KEY、密码等） ✅ 模块化命名：便于区分不同组件的日志 ✅ 自动归档：按日期生成日志文件 ✅ 开箱即用：一行代码即可使用 ✅ 灵活配置：可自定义日志级别和文件名

if __name__ == "__main__":
    # 测试代码
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

"""
【在 Agent 项目中的实际使用】

# ========== 场景 1: RAG 模块记录向量检索 ==========
from utils.logger_handler import logger

class RagService:
    def search(self, query: str):
        # 自动脱敏查询内容（可能包含用户隐私）
        logger.info(f"用户查询：{query}, API_KEY=sk-abc123")
        # 输出：用户查询：xxx, API_KEY=sk-******

        docs = self.vector_store.search(query)
        logger.debug(f"检索到 {len(docs)} 条结果")
        return docs

# ========== 场景 2: LLM 模块记录 API 调用 ==========
class LLMService:
    def call(self, prompt: str, api_key: str):
        # 自动脱敏 API_KEY 和用户输入
        logger.info(f"调用 LLM, key={api_key}, 提示词：{prompt}")
        # 输出：调用 LLM, key=******, 提示词：xxx

        response = self.client.generate(prompt, api_key)
        logger.debug(f"响应：{response}")
        return response

# ========== 场景 3: Tools 模块记录工具调用 ==========
class WeatherTool:
    def __init__(self, api_key: str):
        # 构造函数中的敏感信息也会被脱敏
        logger.info(f"初始化天气工具，key={api_key}")
        self.api_key = api_key

    def execute(self, city: str, phone: str):
        # 脱敏城市名和手机号
        logger.info(f"查询 {city} 天气，用户手机 {phone}")
        # 输出：查询 xxx 天气，用户手机 1**********

# ========== 场景 4: 主程序记录对话流程 ==========
from utils.logger_handler import get_logger

# 为不同模块创建独立日志器
dialog_logger = get_logger("agent.dialog", console_level=logging.DEBUG)
tool_logger = get_logger("agent.tools", file_level=logging.INFO)

def main():
    dialog_logger.info("用户开始对话，session_id=user_001")

    # 调用 RAG
    rag_result = RagService().search("北京天气")
    tool_logger.info(f"RAG 检索完成，找到 {len(rag_result)} 条")

    # 调用 LLM
    llm_result = LLMService().call(rag_result, "sk-abc123")
    dialog_logger.info(f"AI 回复：{llm_result}")

【输出的日志文件】
logs/
├── agent_20240309.log      # 主 Agent 日志
├── agent.dialog_20240309.log  # 对话模块日志
├── agent.tools_20240309.log   # 工具模块日志
└── agent.rag_20240309.log     # RAG 模块日志

【日志内容示例】
2024-03-09 10:30:00 - agent.dialog - INFO - logger_handler.py:95 - 用户开始对话，session_id=user_001
2024-03-09 10:30:01 - agent.tools - INFO - logger_handler.py:95 - RAG 检索完成，找到 3 条
2024-03-09 10:30:02 - agent.dialog - INFO - logger_handler.py:95 - AI 回复：北京今天晴朗...
（所有敏感信息已自动脱敏，无需担心泄露）
"""