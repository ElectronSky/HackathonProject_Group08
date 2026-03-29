"""
AI 财商助手分析服务
负责把“自然语言分析请求”串成完整的分析流程
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

try:
    from ..model.factory import chat_model
    from ..rag.rag_service import RagSummarizeService
    from .analysis_query_parser import parse_analysis_query
    from .evidence_pack_builder import FinanceEvidencePackBuilder
    from .prompt_loader import load_finance_analysis_prompt, load_finance_quick_advice_prompt
except ImportError:
    from importlib import import_module

    chat_model = import_module("model.factory").chat_model
    RagSummarizeService = import_module("rag.rag_service").RagSummarizeService
    parse_analysis_query = import_module("utils.analysis_query_parser").parse_analysis_query
    FinanceEvidencePackBuilder = import_module("utils.evidence_pack_builder").FinanceEvidencePackBuilder
    load_finance_analysis_prompt = import_module("utils.prompt_loader").load_finance_analysis_prompt
    load_finance_quick_advice_prompt = import_module("utils.prompt_loader").load_finance_quick_advice_prompt


class FinanceAnalysisService:
    """
    财商分析服务。

    第一版职责：
    - 接收用户自然语言分析请求；
    - 先解析任务，再构建混合证据包；
    - 在条件合适时补充 RAG 知识支持；
    - 最后生成四段式分析结果。
    """

    def __init__(self):
        """
        初始化分析服务。
        """
        self.prompt_text = load_finance_analysis_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.quick_prompt_text = load_finance_quick_advice_prompt()
        self.quick_prompt_template = PromptTemplate.from_template(self.quick_prompt_text)
        self.model = chat_model
        self.chain = self.prompt_template | self.model | StrOutputParser()
        self.quick_chain = self.quick_prompt_template | self.model | StrOutputParser()
        self._rag_service: Optional[RagSummarizeService] = None

    def analyze_query(self, user_id: str, query: str) -> dict:
        """
        对用户的自然语言分析请求做完整处理。

        Returns:
            dict: 包含分析结果、任务信息、证据包等内容
        """
        builder = FinanceEvidencePackBuilder(user_id)
        catalog = builder.get_analysis_catalog()
        parsed_task = parse_analysis_query(
            query,
            available_categories=catalog["categories"],
            subcategory_to_category=catalog["subcategory_to_category"],
        )

        if parsed_task["query_mode"] == "unsupported":
            return {
                "analysis_markdown": self._build_unsupported_markdown(query),
                "parsed_task": parsed_task,
                "evidence_pack": None,
                "rag_context": "",
                "llm_used": False,
                "rag_used": False,
            }

        evidence_pack = builder.build(parsed_task)
        rag_context = self._get_rag_context(query, parsed_task, evidence_pack)

        # 如果当前没有可分析的数据，直接返回稳定的空数据提示，不强行调用模型
        if not evidence_pack["data_availability"]["has_transactions"]:
            if parsed_task["query_mode"] == "quick_advice":
                analysis_markdown = self._build_quick_advice_empty_markdown(parsed_task, evidence_pack)
            else:
                analysis_markdown = self._build_empty_state_markdown(parsed_task, evidence_pack)
            return {
                "analysis_markdown": analysis_markdown,
                "parsed_task": parsed_task,
                "evidence_pack": evidence_pack,
                "rag_context": rag_context,
                "llm_used": False,
                "rag_used": bool(rag_context),
            }

        llm_used = True
        try:
            if parsed_task["query_mode"] == "quick_advice":
                analysis_markdown = self.quick_chain.invoke({
                    "user_query": query,
                    "analysis_task": json.dumps(parsed_task, ensure_ascii=False, indent=2),
                    "evidence_pack": self._format_evidence_pack(evidence_pack),
                    "rag_context": rag_context or "暂无额外知识检索结果",
                })
            else:
                analysis_markdown = self.chain.invoke({
                    "user_query": query,
                    "analysis_task": json.dumps(parsed_task, ensure_ascii=False, indent=2),
                    "evidence_pack": self._format_evidence_pack(evidence_pack),
                    "rag_context": rag_context or "暂无额外知识检索结果",
                })
        except Exception:
            # 如果外部模型、网络或 API 环境异常，就回退到程序化输出，保证功能不完全失效
            if parsed_task["query_mode"] == "quick_advice":
                analysis_markdown = self._build_rule_based_quick_advice_markdown(parsed_task, evidence_pack, rag_context)
            else:
                analysis_markdown = self._build_rule_based_markdown(parsed_task, evidence_pack, rag_context)
            llm_used = False

        return {
            "analysis_markdown": analysis_markdown,
            "parsed_task": parsed_task,
            "evidence_pack": evidence_pack,
            "rag_context": rag_context,
            "llm_used": llm_used,
            "rag_used": bool(rag_context),
        }

    def _get_rag_context(self, query: str, parsed_task: dict, evidence_pack: dict) -> str:
        """
        在需要时获取财商知识支持。

        第一版策略：
        - 如果用户明显是在问“问题 / 建议 / 为什么”，优先补知识支持；
        - 如果当前证据包已经检测到问题信号，也优先补知识支持；
        - 若知识检索失败，静默回退，不阻塞主分析流程。
        """
        should_use_rag = parsed_task.get("requires_knowledge_support", False) or bool(evidence_pack["problem_signals"])
        if not should_use_rag:
            return ""

        try:
            if self._rag_service is None:
                self._rag_service = RagSummarizeService()

            knowledge_query = self._build_knowledge_query(parsed_task, evidence_pack, query)
            if not self._rag_service.retriever_docs(knowledge_query):
                return ""
            return self._rag_service.rag_summarize(knowledge_query)
        except Exception:
            return ""

    def _build_knowledge_query(self, parsed_task: dict, evidence_pack: dict, user_query: str) -> str:
        """
        为 RAG 构造更聚焦的知识查询。
        """
        signal_titles = [signal["title"] for signal in evidence_pack["problem_signals"]]
        focus_parts = []

        if parsed_task.get("focus_category"):
            focus_parts.append(f"关注类别：{parsed_task['focus_category']}")
        if parsed_task.get("focus_subcategory"):
            focus_parts.append(f"关注子类别：{parsed_task['focus_subcategory']}")
        if signal_titles:
            focus_parts.append(f"问题信号：{'、'.join(signal_titles)}")

        if not focus_parts:
            focus_parts.append("给年轻人做消费复盘和省钱建议")

        return f"{user_query}。请重点提供与 {'；'.join(focus_parts)} 相关的财商知识解释和小建议。"

    def _format_evidence_pack(self, evidence_pack: dict) -> str:
        """
        将证据包转换成适合大模型阅读的文本。
        """
        task_meta = evidence_pack["task_meta"]
        summary = evidence_pack["selected_summary"]
        selected_statistics = evidence_pack.get("selected_statistics", {})
        comparison_summary = evidence_pack["comparison_summary"]
        budget_context = evidence_pack["budget_context"]
        problem_signals = evidence_pack["problem_signals"]
        sample_transactions = evidence_pack["sample_transactions"]

        lines = [
            "[任务元信息]",
            f"- 当前分析任务：{task_meta['intent_label']}",
            f"- 分析范围：{task_meta['time_label']}",
            f"- 起止日期：{task_meta['start_date']} ~ {task_meta['end_date']}",
            f"- 聚焦类别：{task_meta['focus_category'] or '无'}",
            f"- 聚焦子类别：{task_meta['focus_subcategory'] or '无'}",
            f"- 是否自动回退到全部历史数据：{'是' if task_meta['used_all_data_fallback'] else '否'}",
            "",
            "[当前范围核心统计]",
            f"- 交易笔数：{summary['transaction_count']}",
            f"- 总支出：¥{summary['total_amount']:.2f}",
            f"- 平均每笔：¥{summary['average_amount']:.2f}",
            f"- 活跃消费天数：{summary['active_days']}",
            f"- 小额高频交易数（<=20 元）：{summary['small_transaction_count']}",
            f"- 高金额交易数：{summary['high_value_transaction_count']}",
            f"- 最高单笔金额：¥{summary['max_amount']:.2f}",
        ]

        if summary["top_categories"]:
            lines.append("- 主要类别：")
            for item in summary["top_categories"]:
                lines.append(
                    f"  - {item['name']}：¥{item['amount']:.2f}，{item['count']} 笔，占比 {item['ratio'] * 100:.1f}%"
                )

        if summary.get("monthly_trend"):
            lines.append("- 最近月度趋势：")
            for item in summary["monthly_trend"]:
                lines.append(
                    f"  - {item['period']}：¥{item['total_amount']:.2f}，{item['count']} 笔，占该分析时段 {item['ratio'] * 100:.1f}%"
                )

        if summary.get("yearly_trend"):
            lines.append("- 年度趋势：")
            for item in summary["yearly_trend"]:
                lines.append(
                    f"  - {item['period']}：¥{item['total_amount']:.2f}，{item['count']} 笔，占该分析时段 {item['ratio'] * 100:.1f}%"
                )

        amount_level_ratio = summary.get("amount_level_ratio", {})
        if amount_level_ratio:
            lines.append("- 金额区间分布：")
            for level, ratio in sorted(amount_level_ratio.items(), key=lambda item: item[1], reverse=True):
                lines.append(f"  - {level}：占交易数 {ratio * 100:.1f}%")

        if summary["top_subcategories"]:
            lines.append("- 高频子类别：")
            for item in summary["top_subcategories"]:
                lines.append(
                    f"  - {item['name']}：{item['count']} 次，累计 ¥{item['amount']:.2f}"
                )

        if comparison_summary:
            lines.extend([
                "",
                "[与上一时间窗口对比]",
                f"- 对比窗口：{comparison_summary['label']}",
                f"- 当前总支出：¥{comparison_summary['current_total']:.2f}",
                f"- 上一窗口总支出：¥{comparison_summary['previous_total']:.2f}",
                f"- 金额变化：¥{comparison_summary['amount_change']:.2f}",
                f"- 变化比例：{comparison_summary['amount_change_ratio'] * 100:.1f}%",
                f"- 笔数变化：{comparison_summary['count_change']}",
            ])

        monthly_summary = budget_context["monthly"]["summary"]
        weekly_summary = budget_context["weekly"]["summary"]
        lines.extend([
            "",
            "[预算上下文]",
            f"- 本月预警类别数：{monthly_summary['warning_count']}",
            f"- 本月超额类别数：{monthly_summary['over_count']}",
            f"- 本周预警类别数：{weekly_summary['warning_count']}",
            f"- 本周超额类别数：{weekly_summary['over_count']}",
        ])

        if problem_signals:
            lines.extend(["", "[问题信号]"])
            for signal in problem_signals:
                lines.append(f"- {signal['title']}（{signal['severity']}）：{signal['detail']}")
        else:
            lines.extend(["", "[问题信号]", "- 当前范围内暂未检测到非常明显的问题信号。"])

        if sample_transactions:
            lines.extend(["", "[代表性交易样本]"])
            for sample in sample_transactions:
                lines.append(
                    f"- {sample['date']}｜{sample['category']}/{sample['subcategory']}｜¥{sample['amount']:.2f}｜{sample['description']}"
                )

        return "\n".join(lines)

    def _build_empty_state_markdown(self, parsed_task: dict, evidence_pack: dict) -> str:
        """
        当当前范围没有数据时，输出稳定的四段式空状态内容。
        """
        task_meta = evidence_pack["task_meta"]
        scope_text = task_meta["time_label"]
        if task_meta["used_all_data_fallback"]:
            scope_text = f"{scope_text}（默认窗口无数据，已自动回退到全部历史数据）"

        return (
            "## 消费概览\n"
            f"- 这次分析范围是：{scope_text}。\n"
            "- 当前范围内暂时没有可用于分析的消费记录。\n\n"
            "## 问题识别\n"
            "- 因为当前范围内没有记录，所以暂时无法判断明显的消费问题。\n\n"
            "## 可执行建议\n"
            "- 你可以先继续自然语言记账，尽量覆盖 7~10 天以上的数据。\n"
            "- 如果你想马上查看整体情况，也可以试试“全部历史数据”或“最近 30 天”的查询方式。\n\n"
            "## 知识支持\n"
            "- 记账数据越连续，后续的消费分析、预算提醒和学习建议会越准确。"
        )

    def _build_quick_advice_empty_markdown(self, parsed_task: dict, evidence_pack: dict) -> str:
        """
        当用户问的是快速判断型问题，但当前缺少足够数据时，返回更轻量的回答。
        """
        task_meta = evidence_pack["task_meta"]
        return (
            "## 直接回答\n"
            "- 目前我还不能很有把握地直接给你这个问题下判断。\n\n"
            "## 判断依据\n"
            f"- 当前参考范围是：{task_meta['time_label']}。\n"
            "- 但这个范围里暂时没有足够的消费记录，证据不够。\n\n"
            "## 小建议\n"
            "- 你可以先多记几笔同类消费，再来问我，我会更容易判断你是不是花得偏多。\n"
            "- 也可以把时间范围说得更明确一点，比如“最近30天奶茶喝得多不多”。"
        )

    def _build_unsupported_markdown(self, query: str) -> str:
        """
        对明显超出当前财商分析范围的问题，返回稳定提示。
        """
        return (
            "## 当前无法处理\n"
            "- 这个问题暂时不属于我当前的财商分析和消费复盘范围。\n\n"
            "## 你可以这样问我\n"
            "- 帮我看看上个月我的消费情况\n"
            "- 帮我看看我消费有什么问题没有\n"
            "- 帮我看看我今年预算执行得怎么样\n"
            "- 我最近 30 天奶茶喝得多不多"
        )

    def _build_rule_based_markdown(self, parsed_task: dict, evidence_pack: dict, rag_context: str) -> str:
        """
        在模型不可用时，使用程序化方式生成第一版四段式输出。
        """
        task_meta = evidence_pack["task_meta"]
        summary = evidence_pack["selected_summary"]
        comparison_summary = evidence_pack["comparison_summary"]
        problem_signals = evidence_pack["problem_signals"]
        sample_transactions = evidence_pack["sample_transactions"]

        overview_lines = [
            f"- 本次分析范围：{task_meta['time_label']}。",
            f"- 当前共记录 {summary['transaction_count']} 笔消费，总支出为 ¥{summary['total_amount']:.2f}，平均每笔约 ¥{summary['average_amount']:.2f}。",
            f"- 这段时间共有 {summary['active_days']} 天发生了消费。",
        ]

        if task_meta.get("focus_category"):
            overview_lines.append(f"- 这次分析重点聚焦在：{task_meta['focus_category']}。")
            if task_meta.get("focus_data_missing"):
                overview_lines.append("- 不过当前窗口里没有命中该类别的记录，所以本次先展示了整体窗口概况。")

        if summary["top_categories"]:
            top_category_text = "，".join(
                f"{item['name']} ¥{item['amount']:.2f}（{item['ratio'] * 100:.1f}%）"
                for item in summary["top_categories"]
            )
            overview_lines.append(f"- 当前范围内金额占比较高的类别有：{top_category_text}。")

        if comparison_summary and comparison_summary["previous_total"] > 0:
            if comparison_summary["amount_change"] >= 0:
                overview_lines.append(
                    f"- 和 {comparison_summary['label']} 相比，你当前支出增加了 ¥{comparison_summary['amount_change']:.2f}。"
                )
            else:
                overview_lines.append(
                    f"- 和 {comparison_summary['label']} 相比，你当前支出减少了 ¥{abs(comparison_summary['amount_change']):.2f}。"
                )

        problem_lines = []
        if problem_signals:
            for signal in problem_signals:
                problem_lines.append(f"- {signal['title']}：{signal['detail']}")
        else:
            problem_lines.append("- 从当前这段数据看，暂时没有特别突出的风险信号，整体还算平稳。")

        suggestion_lines = self._build_rule_based_suggestions(evidence_pack)

        knowledge_lines = []
        if rag_context:
            knowledge_lines.append(f"- {rag_context}")
        else:
            knowledge_lines.append("- 一般来说，连续记录和定期复盘，会比只看单笔消费更容易发现真正影响支出的习惯模式。")

        if sample_transactions:
            sample_text = "；".join(
                f"{sample['date']} {sample['category']}/{sample['subcategory']} ¥{sample['amount']:.2f}" for sample in sample_transactions[:3]
            )
            knowledge_lines.append(f"- 这次分析参考了部分代表性交易样本，例如：{sample_text}。")

        return (
            "## 消费概览\n"
            + "\n".join(overview_lines)
            + "\n\n## 问题识别\n"
            + "\n".join(problem_lines)
            + "\n\n## 可执行建议\n"
            + "\n".join(suggestion_lines)
            + "\n\n## 知识支持\n"
            + "\n".join(knowledge_lines)
        )

    def _build_rule_based_suggestions(self, evidence_pack: dict) -> list[str]:
        """
        基于证据包中的问题信号，生成第一版规则化建议。
        """
        summary = evidence_pack["selected_summary"]
        problem_signals = evidence_pack["problem_signals"]
        suggestion_lines = []
        signal_titles = {signal["title"] for signal in problem_signals}

        if "单一类别支出占比较高" in signal_titles and summary["top_categories"]:
            top_category = summary["top_categories"][0]
            suggestion_lines.append(
                f"- 你可以先重点复盘 `{top_category['name']}` 这个类别，看看它里面有没有几笔其实可以延后或替代的支出。"
            )

        if "小额高频支出较多" in signal_titles:
            suggestion_lines.append(
                "- 你可以先从小额高频消费入手，例如给零食、饮品或随手买的小东西设一个更清晰的每周上限。"
            )

        if "存在预算超额风险" in signal_titles or "存在预算预警" in signal_titles:
            suggestion_lines.append(
                "- 你可以优先检查已经预警或超额的类别，把本周或本月剩余预算先算清楚，再决定接下来的可选消费。"
            )

        if "支出较上一窗口明显上升" in signal_titles:
            suggestion_lines.append(
                "- 如果最近支出突然上涨，建议你先区分“必要支出”和“可延后支出”，避免短时间内连续放大消费。"
            )

        if not suggestion_lines:
            suggestion_lines.append("- 你可以继续保持连续记账，并每周固定抽一次时间复盘最常出现的消费类别。")
            suggestion_lines.append("- 如果你想看得更细，可以继续追问某个类别或某个时间范围的消费情况。")

        return suggestion_lines

    def _build_rule_based_quick_advice_markdown(self, parsed_task: dict, evidence_pack: dict, rag_context: str) -> str:
        """
        在模型不可用时，为快速判断型问题生成更直接的回答。
        """
        summary = evidence_pack["selected_summary"]
        problem_signals = evidence_pack["problem_signals"]
        task_meta = evidence_pack["task_meta"]

        direct_answer = "- 从当前记录看，可以适度，但不建议毫无节制地继续增加这类消费。"
        if not summary["transaction_count"]:
            direct_answer = "- 我暂时不能直接判断，因为当前范围里没有足够的相关消费记录。"
        elif any(signal["title"] in ["小额高频支出较多", "单一类别支出占比较高", "存在预算超额风险", "存在预算预警"] for signal in problem_signals):
            direct_answer = "- 从当前记录看，我不太建议你继续放宽这类消费，至少要先控制一下频率或预算。"

        reason_lines = [
            f"- 这次主要参考的是：{task_meta['time_label']}。",
            f"- 当前范围内共有 {summary['transaction_count']} 笔相关消费，总金额为 ¥{summary['total_amount']:.2f}。",
        ]

        if summary["top_subcategories"]:
            top_subcategory = summary["top_subcategories"][0]
            reason_lines.append(
                f"- 当前最常出现的细分类是 {top_subcategory['name']}，共 {top_subcategory['count']} 次。"
            )

        if problem_signals:
            reason_lines.append(f"- 当前检测到的主要信号包括：{'、'.join(signal['title'] for signal in problem_signals[:2])}。")
        else:
            reason_lines.append("- 当前没有检测到特别突出的风险信号，所以结论相对宽松一些。")

        advice_lines = [
            "- 如果你想继续买，可以先给自己设一个更清晰的小上限，比如本周最多再买 1~2 次。",
            "- 如果你想让我判断得更准，可以继续问得更具体，比如‘最近30天奶茶是不是有点多’。",
        ]

        if rag_context:
            advice_lines.append(f"- 补充一点知识依据：{rag_context}")

        return (
            "## 直接回答\n"
            + direct_answer
            + "\n\n## 判断依据\n"
            + "\n".join(reason_lines)
            + "\n\n## 小建议\n"
            + "\n".join(advice_lines)
        )


if __name__ == "__main__":
    service = FinanceAnalysisService()
    demo_result = service.analyze_query("user_001", "帮我看看上个月我的消费情况")
    print(demo_result["analysis_markdown"])

