
# cd D:\D-Disk\work\coding\agent\agent_learning\AGENT_BUILDING\agent_project

#提示词加载器中枢
#系统提示词，rag提示词，报告提示词，与抓取对应报错
#三个提示词分别负责系统背景设定，rag提示词整合，最终输出喂给model前整理的提示词

#------------------------------------------#
# 文件名创建时 导包时 调用时 需要一致 不要打错
# 不要用自动补全代码对需要跨文件夹文件名填写的内容，否则容易出错
#------------------------------------------#

# 支持相对导入和直接运行两种方式
try:
    from .config_handler import prompts_conf
except ImportError:
    from config_handler import prompts_conf

try:
    from .path_tools import get_abs_path
except ImportError:
    from path_tools import get_abs_path

try:
    from .logger_handler import logger
except ImportError:
    from logger_handler import logger


#主提示词
def load_system_prompt():

    try:
        #prompts_conf是config_handler里的一个提示词，调用了他的yaml方法得到了prompts.yml中的三个提示词为一个字典，用字典形式调用即可
        #得到了prompt.yaml中存储的提示词的路径存在system_prompt_path
        system_prompt_path = get_abs_path(prompts_conf["main_prompt_path"])
    #路径没找着
    except KeyError as e:
        logger.error(f"[load_system_prompt]解析系统提示词文件路径失败。")
        # 抛出异常
        raise e

    #打开system_prompt_path对应文件内的提示词内容
    try:
        return open(system_prompt_path, "r", encoding="utf-8").read()
    #没找到这个路径里的文件
    except FileNotFoundError as e:
        logger.error(f"[load_system_prompt]系统提示词文件{system_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_system_prompt]解析系统提示词{system_prompt_path}失败. {str(e)}")
        raise e

#rag提示词同上
def load_rag_prompts():
    try:
        rag_summarize_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_rag_prompts]解析系统提示词文件路径失败。")
        raise e

    try:
        return open(rag_summarize_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_rag_prompts]rag提示词文件{rag_summarize_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_rag_prompts]解析rag提示词{rag_summarize_prompt_path}失败. {str(e)}")
        raise e


#报告提示词同上
def load_report_prompt():
    try:
        report_prompt_path = get_abs_path(prompts_conf["report_prompt_path"])
    except KeyError as e:
        logger.error(f"[report_prompt_path]解析系统提示词文件路径失败。")
        raise e

    try:
        return open(report_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[report_prompt_path]报告提示词文件{report_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[report_prompt_path]解析报告提示词{report_prompt_path}失败. {str(e)}")
        raise e


def load_finance_agent_prompt():
    """
    加载财商分析专用 ReAct 主提示词。
    """
    try:
        finance_agent_prompt_path = get_abs_path(prompts_conf["finance_agent_prompt_path"])
    except KeyError as e:
        logger.error("[load_finance_agent_prompt]解析财商主提示词文件路径失败。")
        raise e

    try:
        return open(finance_agent_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_finance_agent_prompt]财商主提示词文件{finance_agent_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_finance_agent_prompt]解析财商主提示词{finance_agent_prompt_path}失败. {str(e)}")
        raise e


def load_finance_report_prompt():
    """
    加载财商分析专用报告提示词。
    """
    try:
        finance_report_prompt_path = get_abs_path(prompts_conf["finance_report_prompt_path"])
    except KeyError as e:
        logger.error("[load_finance_report_prompt]解析财商报告提示词文件路径失败。")
        raise e

    try:
        return open(finance_report_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_finance_report_prompt]财商报告提示词文件{finance_report_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_finance_report_prompt]解析财商报告提示词{finance_report_prompt_path}失败. {str(e)}")
        raise e


def load_finance_analysis_prompt():
    """
    加载 AI 财商助手分析提示词。
    """
    try:
        finance_analysis_prompt_path = get_abs_path(prompts_conf["finance_analysis_prompt_path"])
    except KeyError as e:
        logger.error("[load_finance_analysis_prompt]解析财商分析提示词文件路径失败。")
        raise e

    try:
        return open(finance_analysis_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_finance_analysis_prompt]财商分析提示词文件{finance_analysis_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_finance_analysis_prompt]解析财商分析提示词{finance_analysis_prompt_path}失败. {str(e)}")
        raise e


def load_finance_quick_advice_prompt():
    """
    加载 AI 财商助手快速判断提示词。
    """
    try:
        finance_quick_advice_prompt_path = get_abs_path(prompts_conf["finance_quick_advice_prompt_path"])
    except KeyError as e:
        logger.error("[load_finance_quick_advice_prompt]解析财商快速回答提示词文件路径失败。")
        raise e

    try:
        return open(finance_quick_advice_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_finance_quick_advice_prompt]财商快速回答提示词文件{finance_quick_advice_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_finance_quick_advice_prompt]解析财商快速回答提示词{finance_quick_advice_prompt_path}失败. {str(e)}")
        raise e


def load_finance_time_parse_prompt():
    """
    加载财商助手时间解析提示词。
    """
    try:
        finance_time_parse_prompt_path = get_abs_path(prompts_conf["finance_time_parse_prompt_path"])
    except KeyError as e:
        logger.error("[load_finance_time_parse_prompt]解析时间解析提示词文件路径失败。")
        raise e

    try:
        return open(finance_time_parse_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_finance_time_parse_prompt]时间解析提示词文件{finance_time_parse_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_finance_time_parse_prompt]解析时间解析提示词{finance_time_parse_prompt_path}失败. {str(e)}")
        raise e


def load_card_recommendation_prompt():
    """
    加载知识卡片推荐提示词。
    """
    try:
        card_recommendation_prompt_path = get_abs_path(prompts_conf["card_recommendation_prompt_path"])
    except KeyError as e:
        logger.error("[load_card_recommendation_prompt]解析卡片推荐提示词文件路径失败。")
        raise e

    try:
        return open(card_recommendation_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_card_recommendation_prompt]卡片推荐提示词文件{card_recommendation_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_card_recommendation_prompt]解析卡片推荐提示词{card_recommendation_prompt_path}失败. {str(e)}")
        raise e


def load_card_evaluation_prompt():
    """
    加载知识卡片评估提示词。
    """
    try:
        card_evaluation_prompt_path = get_abs_path(prompts_conf["card_evaluation_prompt_path"])
    except KeyError as e:
        logger.error("[load_card_evaluation_prompt]解析卡片评估提示词文件路径失败。")
        raise e

    try:
        return open(card_evaluation_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_card_evaluation_prompt]卡片评估提示词文件{card_evaluation_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_card_evaluation_prompt]解析卡片评估提示词{card_evaluation_prompt_path}失败. {str(e)}")
        raise e


def load_income_allocation_prompt():
    """
    加载收入分配建议提示词。
    """
    try:
        income_allocation_prompt_path = get_abs_path(prompts_conf["income_allocation_prompt_path"])
    except KeyError as e:
        logger.error("[load_income_allocation_prompt]解析收入分配提示词文件路径失败。")
        raise e

    try:
        return open(income_allocation_prompt_path, "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        logger.error(f"[load_income_allocation_prompt]收入分配提示词文件{income_allocation_prompt_path}不存在. {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"[load_income_allocation_prompt]解析收入分配提示词{income_allocation_prompt_path}失败. {str(e)}")
        raise e


def _load_user_profile_context(user_id: str) -> str:
    """
    加载用户画像上下文，供提示词注入使用。
    
    Args:
        user_id: 用户ID
    
    Returns:
        用户上下文字符串，如果用户画像不存在则返回空字符串
    """
    try:
        # 使用try-import处理相对导入和绝对导入两种情况
        try:
            from utils.user_profile_manager import UserProfileManager
        except ImportError:
            try:
                from ..utils.user_profile_manager import UserProfileManager
            except ImportError:
                from utils.user_profile_manager import UserProfileManager
        
        profile_manager = UserProfileManager(user_id)
        if not profile_manager.is_initialized():
            # 调试日志
            print(f"[prompt_loader] 用户 {user_id} 画像未初始化，返回空上下文")
            return ""
        
        # 构建用户上下文块
        context_block = profile_manager.build_user_context_block()
        personality_rules = profile_manager.build_personality_rules()
        
        # 调试日志：打印生成的上下文
        combined = f"{context_block}{personality_rules}"
        print(f"[prompt_loader] 用户 {user_id} 画像上下文长度: {len(combined)} 字符")
        if combined:
            print(f"[prompt_loader] 上下文预览: {combined[:200]}...")
        return combined
    except Exception as e:
        print(f"[prompt_loader] 加载用户画像上下文失败: {e}")
        return ""


def load_finance_agent_prompt_with_profile(user_id: str):
    """
    加载财商分析专用 ReAct 主提示词，并注入用户画像上下文。
    
    Args:
        user_id: 用户ID
    
    Returns:
        包含用户上下文的提示词字符串
    """
    base_prompt = load_finance_agent_prompt()
    user_context = _load_user_profile_context(user_id)
    
    if user_context:
        # 将用户上下文注入到提示词末尾（在约束之前）
        return f"{base_prompt}\n{user_context}"
    return base_prompt


def load_finance_report_prompt_with_profile(user_id: str):
    """
    加载财商分析专用报告提示词，并注入用户画像上下文。
    
    Args:
        user_id: 用户ID
    
    Returns:
        包含用户上下文的报告提示词字符串
    """
    base_prompt = load_finance_report_prompt()
    user_context = _load_user_profile_context(user_id)
    
    if user_context:
        return f"{base_prompt}\n{user_context}"
    return base_prompt

if __name__ == '__main__':
    print(load_system_prompt())
    print(load_rag_prompts())
    print(load_report_prompt())
    print(load_finance_agent_prompt())
    print(load_finance_report_prompt())
    print(load_finance_analysis_prompt())
    print(load_finance_quick_advice_prompt())
    print(load_finance_time_parse_prompt())
    print(load_card_recommendation_prompt())
    print(load_card_evaluation_prompt())








