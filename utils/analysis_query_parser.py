"""
AI 财商助手查询解析器
负责把用户的自然语言分析需求，解析成结构化分析任务
"""

from datetime import date
from typing import Optional

try:
    from .finance_time_parser import FinanceTimeParser
except ImportError:
    from importlib import import_module

    FinanceTimeParser = import_module("utils.finance_time_parser").FinanceTimeParser


# 这里集中放意图识别关键词，便于后续统一扩展
INTENT_KEYWORDS = {
    "budget_focus": ["预算", "超支", "超额", "预警", "限额"],
    "problem_check": ["问题", "毛病", "不合理", "优化", "建议", "改进", "控制", "分析", "习惯"],
}


# 这些词用于帮助判断用户更偏“想看情况”还是“想找问题”
OVERVIEW_HINTS = ["消费情况", "花了多少", "看看消费", "概览", "总结", "情况"]


# 这些词用于识别“快速判断型”问题，而不是完整报告型问题
QUICK_ADVICE_HINTS = [
    "可以吗", "可不可以", "能不能", "要不要", "值不值", "划算吗", "多不多", "是不是太多",
    "还能", "还可以", "还能不能", "适不适合", "该不该", "会不会太", "可不可以买",
    "可以再", "还能再", "多买点", "再买点", "再喝点", "再买一杯", "有点多", "花太多", "买太多",
]


# 这些词用于尽量判断用户的问题是否仍处于财商 / 消费分析范围内
FINANCE_CUES = [
    "消费", "花", "买", "支出", "预算", "省钱", "攒钱", "记账", "超支", "超额", "存钱",
    "奶茶", "咖啡", "零食", "饮品", "餐饮", "购物", "娱乐", "交通", "预算执行",
    "外卖", "夜宵", "早餐", "午餐", "晚餐", "复盘", "趋势", "账单", "类别", "占比",
]


# 如果问题中出现这些动作词，也更可能是在请求消费分析
ANALYSIS_ACTION_CUES = [
    "分析", "看看", "复盘", "总结", "帮我看", "想知道", "统计", "执行得怎么样", "控制得怎么样",
]


# 明显不在当前能力范围内的问题关键词
UNSUPPORTED_HINTS = [
    "天气", "黎曼", "数学题", "解方程", "翻译", "股票预测", "彩票", "股价", "写代码", "编程题",
]


def _detect_focus_category(query: str,
                           available_categories: Optional[list[str]] = None,
                           subcategory_to_category: Optional[dict[str, str]] = None) -> tuple[Optional[str], Optional[str]]:
    """
    从查询中识别用户是否在聚焦某个类别或子类别。

    说明：
    - 优先匹配更长的字符串，降低“交通”和“公交”这类短词误伤概率；
    - 若命中子类别，则同时回推一级类别；
    - 这里只做第一版的轻量匹配，不做复杂语义解析。
    """
    normalized_query = query.strip()
    available_categories = available_categories or []
    subcategory_to_category = subcategory_to_category or {}

    sorted_subcategories = sorted(subcategory_to_category.keys(), key=len, reverse=True)
    for subcategory_name in sorted_subcategories:
        if subcategory_name and subcategory_name in normalized_query:
            return subcategory_to_category[subcategory_name], subcategory_name

    sorted_categories = sorted(available_categories, key=len, reverse=True)
    for category_name in sorted_categories:
        if category_name and category_name in normalized_query:
            return category_name, None

    return None, None


def _detect_intent(query: str, focus_category: Optional[str]) -> tuple[str, str]:
    """
    识别用户当前更偏向哪类分析任务。
    """
    normalized_query = query.strip()

    if any(keyword in normalized_query for keyword in INTENT_KEYWORDS["budget_focus"]):
        return "budget_focus", "预算执行分析"

    if any(keyword in normalized_query for keyword in INTENT_KEYWORDS["problem_check"]):
        return "problem_check", "问题识别分析"

    if focus_category:
        return "category_focus", f"{focus_category} 专题分析"

    if any(keyword in normalized_query for keyword in OVERVIEW_HINTS):
        return "overview", "消费概览分析"

    return "overview", "消费概览分析"


def _is_finance_related(query: str,
                        time_range: dict,
                        focus_category: Optional[str],
                        focus_subcategory: Optional[str]) -> bool:
    """
    判断问题是否大致处于当前财商助手的能力范围内。

    设计目标：
    - 尽量宽松，避免把正常消费问题误判为超范围；
    - 只有在明显与消费、预算、记账、财商无关时，才走 unsupported。
    """
    normalized_query = query.strip()

    if focus_category or focus_subcategory:
        return True

    # 如果规则 / LLM 已经识别出明确时间范围，而且问题里还有分析动作词，也优先当作财商分析问题处理
    if time_range.get("explicit") and any(keyword in normalized_query for keyword in ANALYSIS_ACTION_CUES):
        return True

    return any(keyword in normalized_query for keyword in FINANCE_CUES)


def _detect_query_mode(query: str,
                       intent: str,
                       time_range: dict,
                       focus_category: Optional[str],
                       focus_subcategory: Optional[str]) -> tuple[str, str]:
    """
    将用户请求粗分流为：
    - report：完整分析 / 预算执行 / 问题识别
    - quick_advice：先给直接判断，再补简短依据
    - unsupported：明显超出当前能力范围
    """
    normalized_query = query.strip()
    is_finance_related = _is_finance_related(normalized_query, time_range, focus_category, focus_subcategory)

    if not is_finance_related and any(keyword in normalized_query for keyword in UNSUPPORTED_HINTS):
        return "unsupported", "超出当前财商分析范围"

    if any(keyword in normalized_query for keyword in QUICK_ADVICE_HINTS) and is_finance_related:
        return "quick_advice", "快速判断回答"

    if is_finance_related:
        return "report", "标准分析报告"

    return "unsupported", "超出当前财商分析范围"


def parse_analysis_query(query: str,
                         available_categories: Optional[list[str]] = None,
                         subcategory_to_category: Optional[dict[str, str]] = None,
                         today: Optional[date] = None) -> dict:
    """
    将用户的自然语言分析请求转换为结构化分析任务。

    Returns:
        dict: 结构化分析任务信息
    """
    normalized_query = query.strip()
    time_parser = FinanceTimeParser()
    time_range = time_parser.resolve_time_range(normalized_query, today=today)
    focus_category, focus_subcategory = _detect_focus_category(
        normalized_query,
        available_categories=available_categories,
        subcategory_to_category=subcategory_to_category,
    )
    intent, intent_label = _detect_intent(normalized_query, focus_category)
    query_mode, query_mode_label = _detect_query_mode(
        normalized_query,
        intent=intent,
        time_range=time_range,
        focus_category=focus_category,
        focus_subcategory=focus_subcategory,
    )

    return {
        "original_query": normalized_query,
        "query_mode": query_mode,
        "query_mode_label": query_mode_label,
        "intent": intent,
        "intent_label": intent_label,
        "time_range": time_range,
        "focus_category": focus_category,
        "focus_subcategory": focus_subcategory,
        "requires_problem_scan": intent in ["problem_check", "budget_focus"],
        "requires_budget_focus": intent == "budget_focus",
        "requires_knowledge_support": intent in ["problem_check", "budget_focus"] or any(
            hint in normalized_query for hint in ["为什么", "建议", "怎么改", "怎么办"]
        ),
    }


if __name__ == "__main__":
    demo_categories = ["餐饮", "娱乐", "购物", "交通"]
    demo_subcategory_map = {
        "奶茶": "餐饮",
        "零食": "餐饮",
        "游戏": "娱乐",
    }

    demo_queries = [
        "帮我看看上个月我的消费情况",
        "帮我看看我消费有什么问题没有",
        "帮我看看最近7天奶茶花得多不多",
    ]

    for demo_query in demo_queries:
        print(parse_analysis_query(
            demo_query,
            available_categories=demo_categories,
            subcategory_to_category=demo_subcategory_map,
        ))

