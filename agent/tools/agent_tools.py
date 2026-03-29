
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.tools import tool


from rag.rag_service import (RagSummarizeService)


from utils.data_handler import UserDataManager
from utils.category_service import CategoryService
from utils.evidence_pack_builder import FinanceEvidencePackBuilder
from utils.logger_handler import logger
from utils.card_candidate_builder import CardCandidateBuilder
from utils.card_repository import CardRepository
from utils.card_state_manager import CardStateManager
from utils.income_manager import IncomeManager
from utils.account_manager import AccountManager
from utils.points_manager import PointsManager

# 全局用户 ID 变量（单用户模式下使用）
_current_user_id = None

def set_current_user(user_id: Optional[str]):
    """设置当前登录的用户 ID"""
    global _current_user_id
    _current_user_id = user_id

def get_current_user_id() -> str:
    """
    获取当前用户 ID
    
    Returns:
        str: 用户唯一标识符
        
    Raises:
        Exception: 用户未登录时抛出异常
    """
    if _current_user_id is None:
        raise Exception("用户未登录")
    return _current_user_id

rag = RagSummarizeService()


def _validate_date_string(date_text: Optional[str], field_name: str) -> Optional[str]:
    """
    对 agent 传入的日期参数做最小护栏校验。

    说明：
    - 当前方案已经确认不再额外维护复杂的时间规则库；
    - 这里仅做基础格式和合法性校验，避免 tool 因非法日期直接崩掉。
    """
    if not date_text:
        return None

    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return None
    except ValueError:
        return f"{field_name} 必须是 YYYY-MM-DD 格式的有效日期"


def _build_time_label(start_date: Optional[str], end_date: Optional[str]) -> str:
    """
    根据起止日期生成给 evidence pack 使用的时间标签。
    """
    if start_date and end_date:
        return f"{start_date} 至 {end_date}"

    if start_date and not end_date:
        return f"{start_date} 起至今"

    if end_date and not start_date:
        return f"历史起点至 {end_date}"

    return "全部历史数据"


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    """
    把空字符串清洗成 None，避免把无效空值传入 builder。
    """
    if value is None:
        return None

    normalized_value = str(value).strip()
    if normalized_value.lower() in {"none", "null", "nil"}:
        return None

    return normalized_value or None


def _validate_relative_year_consistency(user_query: str,
                                        start_date: Optional[str],
                                        end_date: Optional[str]) -> Optional[str]:
    """
    对最容易出错的“今年 / 去年”相对年份做最小一致性校验。

    说明：
    - 当前 Phase 1 仍然以 agent 自己理解时间为主，不回退成大规模规则解析；
    - 但像“今天是 2026 年，却把 去年 解析成 2023 年”这种错误，
      会直接影响展示效果，因此这里补一层非常小的防呆护栏；
    - 如果用户 query 本身已经写了明确的 4 位年份，则尊重用户显式输入，不做这层校验。
    """
    normalized_query = _normalize_optional_text(user_query) or ""
    if not normalized_query or not start_date or not end_date:
        return None

    # 用户已经显式写了 4 位年份时，不把它视为“相对年份”场景。
    if any(char.isdigit() for char in normalized_query) and any(token in normalized_query for token in ["202", "201", "203"]):
        return None

    current_year = datetime.now().year
    start_year = datetime.strptime(start_date, "%Y-%m-%d").year
    end_year = datetime.strptime(end_date, "%Y-%m-%d").year

    # 这里只拦截最关键、最直观的“去年 / 今年”错误，避免重新走回大规则库路线。
    if "去年" in normalized_query and "前年" not in normalized_query and "今年" not in normalized_query:
        expected_year = current_year - 1
        if start_year != expected_year or end_year != expected_year:
            return f"当前日期是 {current_year} 年，query 中的“去年”应解析为 {expected_year} 年，请先调用 get_current_time 后重新计算日期范围"

    if "今年" in normalized_query and "去年" not in normalized_query:
        expected_year = current_year
        if start_year != expected_year or end_year != expected_year:
            return f"当前日期是 {current_year} 年，query 中的“今年”应解析为 {expected_year} 年，请先调用 get_current_time 后重新计算日期范围"

    return None


#工具区
# 把 RAG 检索打包成一个工具，返回一个大模型对当前 query 基于向量库的相关检索结果（完成一个基础 RAG 项目循环）
@tool(description = "从向量存储中检索参考资料")
def rag_summarize(query: str):
    return rag.rag_summarize(query)


@tool(
    description="当用户提出一个消费陈述，或者在 ai财商助手 页面提出相对时间的分析问题时，先调用这个工具获取当前的日期和时间。无入参。")
def get_current_time():
    """
    获取当前日期和时间
    
    Returns:
        str: 格式化的日期时间字符串（YYYY-MM-DD HH:MM:SS）
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(
    description="当用户提出一个消费陈述，在调用 record_expense 之前，先调用这个工具获取所有的预设已有消费类别及每个类别对应的子类别。无入参。")
def get_categories() -> str:
    """
    获取用户已定义的消费类别列表
    
    Returns:
        list: 消费类别列表
    """
    classifier = CategoryService()
    return classifier.get_all_categories()


def _build_budget_transition_reminders(manager: UserDataManager,
                                      category: str,
                                      reference_date,
                                      before_status_map: dict) -> list:
    """
    生成记账后的预算即时提醒。

    设计原则：
    - 只在预算状态发生“升级”时提醒，避免同一类别反复重复提示；
    - 同时检查 weekly / monthly 两个周期；
    - 提醒内容尽量直接说明当前预算状态和超额/剩余额度。
    """
    reminder_lines = []
    status_priority = {
        "normal": 0,
        "warning": 1,
        "over": 2,
    }

    for period in ["weekly", "monthly"]:
        previous_status = before_status_map.get(period)
        current_status = manager.get_category_budget_status(
            category=category,
            period=period,
            reference_date=reference_date,
        )

        # 该类别当前周期没有设置预算时，不生成提醒
        if current_status is None:
            continue

        previous_level = status_priority.get(
            previous_status["status"] if previous_status else "normal",
            0
        )
        current_level = status_priority.get(current_status["status"], 0)

        # 只有从正常 -> 预警 / 超额，或从预警 -> 超额时才触发即时提醒
        if current_level <= previous_level:
            continue

        if current_status["status"] == "warning":
            reminder_lines.append(
                f"⚠️ 预算预警：{category} 在 {current_status['display_label']} 已使用 "
                f"{current_status['usage_ratio'] * 100:.1f}% ，剩余 ¥{max(current_status['remaining'], 0):.2f}。"
            )
        elif current_status["status"] == "over":
            reminder_lines.append(
                f"🚨 预算超额：{category} 在 {current_status['display_label']} 已超出 "
                f"¥{current_status['over_amount']:.2f}（预算 ¥{current_status['budget']:.2f}，"
                f"当前已用 ¥{current_status['spent']:.2f}）。"
            )

    return reminder_lines


@tool(
    description="当用户提出一个消费陈述，使用此工具记录用户的消费信息。传入参数：category(类别 (必须是 get_all_categories 工具获取的已有的 category 消费类别)), amount(金额), description(用户对这个消费的有效描述), date(消费完成时的日期，以 YYYY-MM-DD 形式), subcategory(必须是 get_all_categories 工具获取的已有的 category 消费类别的 sub_categories 内的子消费类别，如有符合，则添加，不然就不添加这个参数)")
def record_expense(category: str, amount: float, description: str,
                   date, subcategory: str = None) -> str:
    """
    自然语言记账核心工具
    
    Args:
        category: 消费类别（餐饮/交通/购物等）
        subcategory: 子消费类别
        amount: 消费金额
        description: 消费描述
        date: 消费日期（可选，默认今天）
    
    Returns:
        str: 格式化成功消息或错误信息
    """
    try:
        # 直接使用本模块定义的全局函数获取用户 ID
        user_id = get_current_user_id()
        
        manager = UserDataManager(user_id)

        # 记账前先获取该类别的预算状态，后续用于判断本次交易是否跨过预警线或超额线
        before_status_map = {
            "weekly": manager.get_category_budget_status(category, period="weekly", reference_date=date),
            "monthly": manager.get_category_budget_status(category, period="monthly", reference_date=date),
        }
    
        transaction = manager.add_transaction({
            "category": category,
            "amount": amount,
            "description": description,
            "date": date,
            "subcategory": subcategory,
        })

        budget_reminders = _build_budget_transition_reminders(
            manager=manager,
            category=transaction["category"],
            reference_date=transaction["date"],
            before_status_map=before_status_map,
        )

        # ==================== Phase 4.5 扩展：记账成功后添加积分奖励 ====================
        try:
            points_manager = PointsManager(user_id)
            points_result = points_manager.add_points(
                action="record_expense",
                description=f"记账奖励 - {transaction['category']} ¥{transaction['amount']}"
            )
            points_earned = points_result.get("points_earned", 0)
            current_balance = points_result.get("balance_after", 0)
        except Exception as e:
            # 积分添加失败不影响主流程
            logger.warning(f"[record_expense]添加积分奖励失败: {str(e)}")
            points_earned = 0
            current_balance = None

        response_text = (f"✓ 记账成功\n"
                         f"类别：{transaction['category']}\n"
                         f"子类别：{transaction['subcategory']}\n"
                         f"金额：¥{transaction['amount']}\n"
                         f"描述：{transaction['description']}\n"
                         f"时间：{transaction['date']}\n"
                         f"消费 id：{transaction['transaction_id']}")

        if budget_reminders:
            response_text += "\n\n=== 预算提醒 ===\n" + "\n".join(budget_reminders)
        
        # 添加积分奖励反馈
        if points_earned > 0:
            response_text += f"\n\n🎁 **记账奖励：+{points_earned} 积分** | 当前余额：{current_balance} 分"
    
        return response_text
    
    except Exception as e:
        return f"✗ 记账失败：{str(e)}"

@tool(description="根据具体需求（传入参数作为filter），获取用户的各种消费数据。支持按日期范围(YYYY-MM-DD格式)、消费类别进行过滤查询。可单独使用或组合使用多个过滤条件。" )
def get_all_data(start_date: str = None, end_date: str = None, category: str = None) -> str:
    """
    获取用户消费数据（支持多种过滤条件）

    Args:
        start_date: 查询起始日期 (YYYY-MM-DD格式)
        end_date: 查询截止日期 (YYYY-MM-DD 格式)
        category: 消费类别名称

    Returns:
        str: 简化后的消费数据，格式为"日期, 金额, 类别, 子类别"
    """
    user_id = get_current_user_id()
    manager = UserDataManager(user_id)
    transactions = manager.get_all_transactions()

    # 应用过滤条件
    filtered_transactions = []
    for transaction in transactions:
        # 日期范围过滤
        if start_date and transaction['date'] < start_date:
            continue
        if end_date and transaction['date'] > end_date:
            continue
        # 类别过滤
        if category and transaction['category'] != category:
            continue
        filtered_transactions.append(transaction)

    if not filtered_transactions:
        return "根据指定条件未找到相关数据"

    result = "基础消费数据如下，每一条的格式：时间，消费金额，类别，子类别 \n"
    for transaction in filtered_transactions:
        # 四舍五入金额到整数
        amount = round(float(transaction['amount']))
        result += f"{transaction['date']}, {amount}, {transaction['category']}, {transaction['subcategory']} \n"

        # 添加分隔符
    result += "\n=== 统计分析 ===\n"

    # 调用get_statistics_by_filter获取统计结果
    statistics = manager.get_statistics_by_filter(
        start_date=start_date,
        end_date=end_date,
        category=category,
    )

    # 将统计结果转换为自然语言并追加到result后面

    # 1. 类别统计
    if statistics["category_stats"]:
        result += "\n[类别统计]\n"
        for cat, stats in sorted(statistics["category_stats"].items(),
                                 key=lambda x: x[1]["total_amount"], reverse=True):
            amount_ratio = statistics["amount_ratio"][cat] * 100
            result += f"{cat}类消费总额¥{stats['total_amount']:.2f}，占总支出{amount_ratio:.1f}%，共{stats['count']}笔交易。\n"

    # 2. 时间维度统计
    if statistics["time_stats"]["monthly"]:
        result += "\n[时间趋势]\n"
        monthly_stats = statistics["time_stats"]["monthly"]
        for month in sorted(monthly_stats.keys()):
            stats = monthly_stats[month]
            ratio = statistics["time_amount_ratio"]["monthly"][month] * 100
            result += f"{month}月消费总额¥{stats['total_amount']:.2f}，占该时段总支出{ratio:.1f}%。\n"

    # 3. 金额区间统计
    result += "\n[金额特征]\n"
    level_ratios = statistics["amount_level_ratio"]
    total_count = sum(stats["count"] for stats in statistics["category_stats"].values())
    for level, ratio in sorted(level_ratios.items(), key=lambda x: x[1], reverse=True):
        count = int(ratio * total_count)
        result += f"{level}的交易占比{ratio * 100:.1f}%，共约{count}笔。\n"

    return result


@tool(
    description=(
        "在 ai财商助手 页面做完整消费分析、问题识别、预算执行分析或某类消费专题分析时，"
        "优先调用这个工具获取结构化财商证据包。"
        "如果用户给的是相对时间表达，应先调用 get_current_time，"
        "再把你自己推导出的 start_date 和 end_date 以 YYYY-MM-DD 格式传入本工具。"
        "可选参数 category 和 subcategory 用于聚焦某个消费大类或子类；"
        "如果用户问的是整体消费情况，就不要乱传 category 或 subcategory。"
    )
)
def build_finance_evidence_pack(
    start_date: str = None,
    end_date: str = None,
    category: str = None,
    subcategory: str = None,
    user_query: str = "",
    analysis_mode: str = "finance_report"
) -> str:
    """
    构建给财商分析 agent 使用的结构化 evidence pack。

    Args:
        start_date: 分析开始日期，格式 YYYY-MM-DD
        end_date: 分析结束日期，格式 YYYY-MM-DD
        category: 聚焦的大类名称，可选
        subcategory: 聚焦的子类名称，可选
        user_query: 用户原始问题，供后续分析和调试参考
        analysis_mode: 当前分析模式标记，便于后续升级

    Returns:
        str: JSON 字符串，包含统计、摘要、预算上下文、问题信号和样本交易等信息
    """
    try:
        # 先把 agent 可能传来的字符串空值（如 "None" / "null"）归一化为真正的 None。
        start_date = _normalize_optional_text(start_date)
        end_date = _normalize_optional_text(end_date)
        user_query = _normalize_optional_text(user_query) or ""
        analysis_mode = _normalize_optional_text(analysis_mode) or "finance_report"

        # 先做最小日期校验，避免 agent 传入非法日期时直接把工具打崩。
        start_date_error = _validate_date_string(start_date, "start_date")
        if start_date_error:
            return json.dumps({"success": False, "error": start_date_error}, ensure_ascii=False)

        end_date_error = _validate_date_string(end_date, "end_date")
        if end_date_error:
            return json.dumps({"success": False, "error": end_date_error}, ensure_ascii=False)

        # 如果起止日期同时存在，再额外检查顺序是否合法。
        if start_date and end_date:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            if parsed_start_date > parsed_end_date:
                return json.dumps({
                    "success": False,
                    "error": "start_date 不能晚于 end_date"
                }, ensure_ascii=False)

        # 对“今年 / 去年”这种最关键的相对年份再做一层一致性保护，
        # 避免 agent 没有先取当前时间时把年份理解错位。
        relative_year_error = _validate_relative_year_consistency(
            user_query=user_query,
            start_date=start_date,
            end_date=end_date,
        )
        if relative_year_error:
            return json.dumps({"success": False, "error": relative_year_error}, ensure_ascii=False)

        # 清洗可选类别参数，避免空字符串污染后续筛选。
        normalized_category = _normalize_optional_text(category)
        normalized_subcategory = _normalize_optional_text(subcategory)

        # 获取当前用户，再复用你已有的 evidence builder 生成主数据包。
        user_id = get_current_user_id()
        builder = FinanceEvidencePackBuilder(user_id)

        # 按当前方案约定，把 agent 传入的日期和聚焦信息封装成 builder 需要的 task 结构。
        task = {
            "intent": "finance_analysis",
            "intent_label": "AI 财商助手分析",
            "time_range": {
                "type": "custom" if start_date or end_date else "all",
                "label": _build_time_label(start_date, end_date),
                "start_date": start_date,
                "end_date": end_date,
                "explicit": bool(start_date or end_date),
            },
            "focus_category": normalized_category,
            "focus_subcategory": normalized_subcategory,
        }

        evidence_pack = builder.build(task)

        # 把这次 agent 调用时的额外上下文补进 task_meta，方便后续 prompt 约束和调试查看。
        evidence_pack["task_meta"]["analysis_mode"] = analysis_mode
        evidence_pack["task_meta"]["user_query"] = user_query

        # ==================== Phase 4 扩展：添加收入和账户数据 ====================
        try:
            # 获取收入统计
            income_manager = IncomeManager(user_id)
            income_summary = income_manager.get_income_summary(
                start_date=start_date,
                end_date=end_date
            )
            
            # 获取账户余额
            account_manager = AccountManager(user_id)
            account_summary = account_manager.get_account_summary()
            
            # 添加到 evidence pack
            evidence_pack["income_summary"] = {
                "total": income_summary.get("total", 0.0),
                "count": income_summary.get("count", 0),
                "by_source": income_summary.get("by_source", {}),
                "savings_total": income_summary.get("savings_total", 0.0),
                "liquid_total": income_summary.get("liquid_total", 0.0),
            }
            evidence_pack["account_summary"] = {
                "savings_balance": account_summary.get("savings_balance", 0.0),
                "liquid_balance": account_summary.get("liquid_balance", 0.0),
                "total_assets": account_summary.get("total_assets", 0.0),
            }
        except Exception as e:
            # 如果收入/账户数据获取失败，记录日志但不阻断主流程
            logger.warning(f"[build_finance_evidence_pack]获取收入/账户数据失败: {str(e)}")
            evidence_pack["income_summary"] = {
                "total": 0.0,
                "count": 0,
                "by_source": {},
                "savings_total": 0.0,
                "liquid_total": 0.0,
            }
            evidence_pack["account_summary"] = {
                "savings_balance": 0.0,
                "liquid_balance": 0.0,
                "total_assets": 0.0,
            }

        # 用统一的 JSON 文本返回，让 agent 能稳定读取字段，不必从自然语言里再反向解析。
        return json.dumps({
            "success": True,
            **evidence_pack,
        }, ensure_ascii=False, indent=2, default=str)

    except Exception as e:
        import traceback
        error_detail = f"[build_finance_evidence_pack]构建财商证据包失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_detail)
        return json.dumps({
            "success": False,
            "error": f"构建财商证据包失败: {str(e)}\n详情请查看日志"
        }, ensure_ascii=False)


def _safe_load_json_text(raw_text: str) -> dict:
    """
    对工具之间传递的 JSON 字符串做最小安全解析。
    """
    if not raw_text:
        return {}

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {}


def _filter_transactions_for_card(manager: UserDataManager,
                                  start_date: Optional[str],
                                  end_date: Optional[str],
                                  card_payload: dict) -> list[dict]:
    """
    根据卡片聚焦条件，提取当前评估窗口内真正相关的交易。
    """
    transactions = manager.get_transactions_by_filters(
        start_date=start_date,
        end_date=end_date,
    )

    focus_category = _normalize_optional_text(card_payload.get("focus_category"))
    focus_subcategories = {
        _normalize_optional_text(item)
        for item in card_payload.get("focus_subcategories", [])
        if _normalize_optional_text(item)
    }

    filtered_transactions = []
    for transaction in transactions:
        transaction_category = _normalize_optional_text(transaction.get("category"))
        transaction_subcategory = _normalize_optional_text(transaction.get("subcategory"))

        if focus_category and transaction_category != focus_category:
            continue

        if focus_subcategories and transaction_subcategory not in focus_subcategories:
            # 如果卡片同时给了 focus_category 和多个子类别，这里优先按子类别收窄；
            # 如果当前交易没有命中指定子类别，就不把它纳入评估窗口。
            continue

        filtered_transactions.append(transaction)

    return filtered_transactions


def _build_card_window_metrics(manager: UserDataManager,
                               start_date: Optional[str],
                               end_date: Optional[str],
                               card_payload: dict) -> dict:
    """
    构建卡片评估专用的窗口指标。
    """
    filtered_transactions = _filter_transactions_for_card(
        manager=manager,
        start_date=start_date,
        end_date=end_date,
        card_payload=card_payload,
    )

    transaction_count = len(filtered_transactions)
    total_amount = round(sum(float(item.get("amount", 0.0)) for item in filtered_transactions), 2)
    active_days = len({item.get("date") for item in filtered_transactions if item.get("date")})
    average_amount = round(total_amount / transaction_count, 2) if transaction_count else 0.0

    subcategory_counter = {}
    for transaction in filtered_transactions:
        subcategory_name = str(transaction.get("subcategory", "未分类")).strip() or "未分类"
        subcategory_counter.setdefault(subcategory_name, {"amount": 0.0, "count": 0})
        subcategory_counter[subcategory_name]["amount"] += float(transaction.get("amount", 0.0))
        subcategory_counter[subcategory_name]["count"] += 1

    subcategory_breakdown = [
        {
            "name": subcategory_name,
            "count": stats["count"],
            "amount": round(stats["amount"], 2),
        }
        for subcategory_name, stats in sorted(
            subcategory_counter.items(),
            key=lambda item: (item[1]["count"], item[1]["amount"]),
            reverse=True,
        )[:5]
    ]

    sample_transactions = [
        {
            "date": item.get("date"),
            "category": item.get("category"),
            "subcategory": item.get("subcategory"),
            "amount": round(float(item.get("amount", 0.0)), 2),
            "description": item.get("description", ""),
        }
        for item in sorted(
            filtered_transactions,
            key=lambda transaction: (transaction.get("date", ""), float(transaction.get("amount", 0.0))),
            reverse=True,
        )[:5]
    ]

    return {
        "window": {
            "start_date": start_date,
            "end_date": end_date,
            "label": _build_time_label(start_date, end_date),
        },
        "transaction_count": transaction_count,
        "total_amount": total_amount,
        "active_days": active_days,
        "average_amount": average_amount,
        "subcategory_breakdown": subcategory_breakdown,
        "sample_transactions": sample_transactions,
    }


def _calculate_previous_window(start_date: str, end_date: str) -> tuple[str, str]:
    """
    根据当前评估窗口推导前一个等长周期。
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    window_days = (end_dt - start_dt).days + 1

    previous_end = start_dt - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)
    return previous_start.strftime("%Y-%m-%d"), previous_end.strftime("%Y-%m-%d")


@tool(
    description=(
        "根据当前分析 evidence pack，为知识卡片系统构建少量候选卡片。"
        "输入 user_query 和 build_finance_evidence_pack 返回的 evidence_pack_json，"
        "输出 JSON 格式的候选列表。"
    )
)
def build_card_candidates(
    user_query: str,
    evidence_pack_json: str,
    max_candidates: int = 5
) -> str:
    try:
        evidence_pack = _safe_load_json_text(evidence_pack_json)
        if not evidence_pack:
            return json.dumps({
                "success": False,
                "candidate_count": 0,
                "candidates": [],
                "error": "evidence_pack_json 解析失败",
            }, ensure_ascii=False)

        user_id = get_current_user_id()
        builder = CardCandidateBuilder(user_id)
        candidates = builder.build_candidates(
            evidence_pack=evidence_pack,
            user_query=user_query,
            max_candidates=max_candidates,
        )
        return json.dumps({
            "success": True,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[build_card_candidates]构建卡片候选失败: {str(e)}")
        return json.dumps({
            "success": False,
            "candidate_count": 0,
            "candidates": [],
            "error": f"构建卡片候选失败: {str(e)}",
        }, ensure_ascii=False)


@tool(description="无入参与返回值，调用后触发中间件自动切换到知识卡片推荐模式提示词。")
def fill_context_for_card_recommendation() -> str:
    return "fill_context_for_card_recommendation 已调用"


@tool(
    description=(
        "保存用户对知识卡片的动作反馈。"
        "user_action 仅支持 accepted / remind_later / view_only。"
    )
)
def save_card_action(
    card_id: str,
    card_title: str,
    user_action: str,
    source_conversation_id: str,
    source_query: str,
    activated_by_time_label: str,
    eval_cycle_days: int
) -> str:
    try:
        user_id = get_current_user_id()
        repository = CardRepository()
        state_manager = CardStateManager(user_id)
        card_payload = repository.get_card_by_id(card_id) or {
            "card_id": card_id,
            "title": card_title,
            "tags": [],
            "doing_text": "",
            "why_text": "",
            "recommended_eval_days": eval_cycle_days,
        }

        card_instance = state_manager.record_card_action(
            card_payload=card_payload,
            user_action=user_action,
            source_conversation_id=source_conversation_id,
            source_query=source_query,
            activated_by_time_label=activated_by_time_label,
            eval_cycle_days=eval_cycle_days,
        )
        return json.dumps({
            "success": True,
            "card_instance_id": card_instance.get("card_instance_id"),
            "next_evaluation_date": card_instance.get("next_evaluation_date"),
            "status": card_instance.get("status"),
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[save_card_action]保存卡片动作失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"保存卡片动作失败: {str(e)}",
        }, ensure_ascii=False)


@tool(
    description=(
        "为知识卡片评估流程构建评估数据包。"
        "输入 card_instance_id，可选 evaluation_start_date 和 evaluation_end_date，"
        "返回当前评估窗口与前一等长窗口的 JSON 数据包。"
    )
)
def build_card_evaluation_pack(
    card_instance_id: str,
    evaluation_start_date: str = None,
    evaluation_end_date: str = None
) -> str:
    try:
        user_id = get_current_user_id()
        state_manager = CardStateManager(user_id)
        repository = CardRepository()
        manager = UserDataManager(user_id)

        card_instance = state_manager.get_card_instance(card_instance_id)
        if not card_instance:
            return json.dumps({
                "success": False,
                "error": "未找到对应的卡片实例",
            }, ensure_ascii=False)

        card_payload = card_instance.get("card_snapshot") or repository.get_card_by_id(card_instance.get("card_id", ""))
        if not card_payload:
            return json.dumps({
                "success": False,
                "error": "未找到对应的卡片原始内容",
            }, ensure_ascii=False)

        normalized_start = _normalize_optional_text(evaluation_start_date)
        normalized_end = _normalize_optional_text(evaluation_end_date)

        if not normalized_end:
            normalized_end = datetime.now().strftime("%Y-%m-%d")

        if not normalized_start:
            eval_cycle_days = max(int(card_instance.get("eval_cycle_days", 7) or 7), 1)
            normalized_start = (
                datetime.strptime(normalized_end, "%Y-%m-%d") - timedelta(days=eval_cycle_days - 1)
            ).strftime("%Y-%m-%d")

        start_date_error = _validate_date_string(normalized_start, "evaluation_start_date")
        if start_date_error:
            return json.dumps({"success": False, "error": start_date_error}, ensure_ascii=False)

        end_date_error = _validate_date_string(normalized_end, "evaluation_end_date")
        if end_date_error:
            return json.dumps({"success": False, "error": end_date_error}, ensure_ascii=False)

        previous_start_date, previous_end_date = _calculate_previous_window(normalized_start, normalized_end)

        current_pack = _build_card_window_metrics(
            manager=manager,
            start_date=normalized_start,
            end_date=normalized_end,
            card_payload=card_payload,
        )
        previous_pack = _build_card_window_metrics(
            manager=manager,
            start_date=previous_start_date,
            end_date=previous_end_date,
            card_payload=card_payload,
        )

        return json.dumps({
            "success": True,
            "card_instance": card_instance,
            "card_payload": card_payload,
            "evaluation_window": {
                "start_date": normalized_start,
                "end_date": normalized_end,
            },
            "current_pack": current_pack,
            "previous_pack": previous_pack,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[build_card_evaluation_pack]构建卡片评估数据包失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"构建卡片评估数据包失败: {str(e)}",
        }, ensure_ascii=False)


@tool(description="无入参与返回值，调用后触发中间件自动切换到知识卡片评估模式提示词。")
def fill_context_for_card_evaluation() -> str:
    return "fill_context_for_card_evaluation 已调用"


# ==================== 收入记录工具 ====================
# 收入类别列表，供 agent 在记录收入时选择
INCOME_CATEGORIES = [
    {"category": "工资", "icon": "💼", "sub_categories": ["月薪", "奖金", "年终奖"]},
    {"category": "兼职", "icon": "💻", "sub_categories": ["实习", "外包", "家教"]},
    {"category": "奖学金", "icon": "🎓", "sub_categories": ["学业奖学金", "竞赛奖金"]},
    {"category": "投资收益", "icon": "📈", "sub_categories": ["利息", "分红"]},
    {"category": "其他收入", "icon": "💵", "sub_categories": ["红包", "退款", "其他"]},
]


@tool(description="当用户提出收入记录需求时（如'收到了工资'、'兼职赚了钱'、'收到了奖学金'等），使用此工具记录用户的收入信息。传入参数：source(收入来源，如工资/兼职/奖学金/投资收益/其他收入), amount(金额，数字), description(描述，可选), date(日期，格式 YYYY-MM-DD，不传则默认今天), savings_ratio(存入储蓄的比例，0-1之间，不传则默认0.1), liquid_ratio(进入流动资金的比例，0-1之间，不传则默认0.9)。")
def record_income(
    source: str,
    amount: float,
    description: str = "",
    date: str = None,
    savings_ratio: float = 0.1,
    liquid_ratio: float = 0.9
) -> str:
    """
    记录用户收入并自动分配到储蓄和流动资金。
    
    Args:
        source: 收入来源
        amount: 收入金额
        description: 收入描述
        date: 收入日期（可选，默认今天）
        savings_ratio: 存入储蓄的比例（默认 0.1，即 10%）
        liquid_ratio: 进入流动资金的比例（默认 0.9，即 90%）
    
    Returns:
        str: 操作结果
    """
    try:
        user_id = get_current_user_id()
        
        # 初始化管理器和账户管理器
        income_manager = IncomeManager(user_id)
        account_manager = AccountManager(user_id)
        
        # 归一化日期
        normalized_date = _normalize_optional_text(date)
        if not normalized_date:
            normalized_date = datetime.now().strftime("%Y-%m-%d")
        
        # 计算分配金额
        savings_amount = round(float(amount) * float(savings_ratio), 2)
        liquid_amount = round(float(amount) * float(liquid_ratio), 2)
        
        # 记录收入
        income_record = income_manager.add_income({
            "category": source,
            "subcategory": "",
            "amount": float(amount),
            "description": description if description else "",
            "date": normalized_date,
            "savings_amount": savings_amount,
            "liquid_amount": liquid_amount,
        })
        
        # 更新账户余额
        account_manager.record_income_allocation(
            income_transaction_id=income_record["transaction_id"],
            savings_change=savings_amount,
            liquid_change=liquid_amount,
            note=f"收入分配 - {source}"
        )
        
        # 构建返回消息
        response_text = (
            f"✅ 收入记录成功\n\n"
            f"📥 **收入来源：** {source}\n"
            f"💰 **收入金额：** ¥{float(amount):,.2f}\n"
            f"📅 **收入日期：** {normalized_date}\n"
            f"📝 **描述：** {description if description else '无'}\n\n"
            f"--- 💎 收入分配 ---\n\n"
            f"🏦 **存入储蓄：** ¥{savings_amount:,.2f}（占比 {float(savings_ratio)*100:.0f}%）\n"
            f"💳 **进入流动资金：** ¥{liquid_amount:,.2f}（占比 {float(liquid_ratio)*100:.0f}%）"
        )
        
        # 显示当前账户状态
        summary = account_manager.get_account_summary()
        response_text += (
            f"\n\n--- 📊 当前账户状态 ---\n\n"
            f"🏦 储蓄账户余额：**¥{summary['savings_balance']:,.2f}**\n"
            f"💳 流动资金余额：**¥{summary['liquid_balance']:,.2f}**\n"
            f"💰 总资产：**¥{summary['total_assets']:,.2f}**"
        )
        
        return response_text
        
    except Exception as e:
        import traceback
        error_detail = f"[record_income]记录收入失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_detail)
        return f"❌ 收入记录失败：{str(e)}"


@tool(description="当用户提出调整储蓄账户或流动资金余额时（如'存了1000块到储蓄'、'取出500块'等），使用此工具手动调整账户余额。传入参数：account_type(savings-储蓄账户/liquid-流动资金), change_amount(变化金额，正数表示存入/增加，负数表示取出/减少), note(调整原因，可选)。注意：当向储蓄账户存入时，资金会自动从流动资金转出；当从储蓄账户取出时，资金会自动转入流动资金。")
def adjust_account_balance(
    account_type: str,
    change_amount: float,
    note: str = ""
) -> str:
    """
    手动调整储蓄账户或流动资金的余额。
    
    说明：
    - 当调整储蓄账户时，AccountManager 会自动联动调整流动资金（反向变动）
    - 当调整流动资金时，储蓄账户不变
    
    Args:
        account_type: "savings" 或 "liquid"
        change_amount: 变化金额（正数增加，负数减少）
        note: 调整原因（可选）
    
    Returns:
        str: 操作结果
    """
    try:
        # 参数校验
        if account_type not in ["savings", "liquid"]:
            return f"❌ 参数错误：account_type 必须是 'savings'（储蓄账户）或 'liquid'（流动资金）"
        
        user_id = get_current_user_id()
        account_manager = AccountManager(user_id)
        
        # 获取调整前的账户余额（用于最终展示）
        summary_before = account_manager.get_account_summary()
        
        # 执行调整（AccountManager 内部会处理储蓄↔流动资金联动）
        result = account_manager.adjust_balance(
            account_type=account_type,
            change_amount=float(change_amount),
            note=note if note else None
        )
        
        # 获取更新后的余额
        summary_after = account_manager.get_account_summary()
        
        # 构建响应消息
        if account_type == "savings":
            # 储蓄账户调整时，展示转账效果
            if float(change_amount) > 0:
                direction = "流动资金 → 储蓄账户"
                savings_display = f"+¥{float(change_amount):,.2f}"
                liquid_display = f"-¥{float(change_amount):,.2f}"
            else:
                direction = "储蓄账户 → 流动资金"
                savings_display = f"¥{float(change_amount):,.2f}"
                liquid_display = f"+¥{abs(float(change_amount)):,.2f}"
            
            response_text = (
                f"✅ 转账成功\n\n"
                f"💱 **转账方向：** {direction}\n"
                f"💰 **转账金额：** ¥{abs(float(change_amount)):,.2f}\n\n"
                f"--- 📊 账户变动 ---\n\n"
                f"🏦 储蓄账户：¥{summary_before['savings_balance']:,.2f} → ¥{summary_after['savings_balance']:,.2f}（{savings_display}）\n"
                f"💳 流动资金：¥{summary_before['liquid_balance']:,.2f} → ¥{summary_after['liquid_balance']:,.2f}（{liquid_display}）"
            )
        else:
            # 流动资金调整时
            change_symbol = "+" if float(change_amount) > 0 else ""
            response_text = (
                f"✅ 流动资金调整成功\n\n"
                f"💹 **变化：** {change_symbol}¥{float(change_amount):,.2f}\n"
                f"💳 **流动资金：** ¥{summary_before['liquid_balance']:,.2f} → ¥{summary_after['liquid_balance']:,.2f}\n"
                f"🏦 **储蓄账户：** ¥{summary_after['savings_balance']:,.2f}（不变）"
            )
        
        if note:
            response_text += f"\n📝 **备注：** {note}"
        
        # 显示当前总资产
        response_text += (
            f"\n\n--- 💎 当前总资产 ---\n\n"
            f"🏦 储蓄账户：**¥{summary_after['savings_balance']:,.2f}**\n"
            f"💳 流动资金：**¥{summary_after['liquid_balance']:,.2f}**\n"
            f"💰 合计：**¥{summary_after['total_assets']:,.2f}**"
        )
        
        return response_text
        
    except ValueError as e:
        return f"❌ 调整失败：{str(e)}"
    except Exception as e:
        import traceback
        error_detail = f"[adjust_account_balance]调整账户余额失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_detail)
        return f"❌ 调整失败：{str(e)}"



external_data = {}
#先设定好模拟数据格式再去读取
#按照美观的自定义格式读取 csv 文件
# def generate_external_data():


#@tool(description="检索指定用户在指定月份的扫地/扫拖机器人完整使用记录，以纯字符形式返回，如未检索到返回空字符串")
#def fetch_external_data(user_id: str, month: str) -> str:


# 动态提示词更换工具。
# 当财商分析 agent 判断证据已经足够时，会调用这个工具。
# 中间件检测到该工具被调用后，会把 runtime.context["report"] 标记为 True。
@tool(description="无入参与返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report() -> str:
    """
    触发财商分析报告模式。
    """
    return "fill_context_for_report 已调用"

if __name__ == "__main__":
    # 本地快速自检时，只保留最基础的时间工具输出，避免引用未实现的示例函数。
    print(get_current_time.invoke({}))
