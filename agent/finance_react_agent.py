import json
import re
from typing import Any, Optional, cast

from langchain.agents import create_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

try:
    from .middleware import monitor_tool, log_before_model, report_prompt_switch
    from .tools.agent_tools import (
        build_card_candidates,
        build_card_evaluation_pack,
        rag_summarize,
        get_current_time,
        get_all_data,
        build_finance_evidence_pack,
        fill_context_for_report,
        get_current_user_id,
        record_income,
        adjust_account_balance,
    )
    from ..model.factory import chat_model
    from ..utils.prompt_loader import (
        load_finance_agent_prompt,
        load_finance_agent_prompt_with_profile,
        load_finance_report_prompt_with_profile,
        load_card_recommendation_prompt,
        load_card_evaluation_prompt,
    )
    from ..utils.card_state_manager import CardStateManager
    from ..utils.model_error_helper import normalize_model_error
except ImportError:
    from importlib import import_module

    middleware_module = import_module("agent.middleware")
    monitor_tool = middleware_module.monitor_tool
    log_before_model = middleware_module.log_before_model
    report_prompt_switch = middleware_module.report_prompt_switch

    tools_module = import_module("agent.tools.agent_tools")
    build_card_candidates = tools_module.build_card_candidates
    build_card_evaluation_pack = tools_module.build_card_evaluation_pack
    rag_summarize = tools_module.rag_summarize
    get_current_time = tools_module.get_current_time
    get_all_data = tools_module.get_all_data
    build_finance_evidence_pack = tools_module.build_finance_evidence_pack
    fill_context_for_report = tools_module.fill_context_for_report
    get_current_user_id = tools_module.get_current_user_id

    chat_model = import_module("model.factory").chat_model
    load_finance_agent_prompt = import_module("utils.prompt_loader").load_finance_agent_prompt
    load_finance_agent_prompt_with_profile = import_module("utils.prompt_loader").load_finance_agent_prompt_with_profile
    load_finance_report_prompt_with_profile = import_module("utils.prompt_loader").load_finance_report_prompt_with_profile
    load_card_recommendation_prompt = import_module("utils.prompt_loader").load_card_recommendation_prompt
    load_card_evaluation_prompt = import_module("utils.prompt_loader").load_card_evaluation_prompt
    CardStateManager = import_module("utils.card_state_manager").CardStateManager
    normalize_model_error = import_module("utils.model_error_helper").normalize_model_error


class FinanceReactAgent:
    """
    财商分析专用 ReAct agent。

    设计说明：
    - 这个 agent 只服务 `🤖 ai财商助手` 页面；
    - 它和自然语言记账页的 ReactAgent 分开，避免工具集和 prompt 串台；
    - 它通过 runtime context 中的 `agent_scene=finance_assistant` 与 middleware 配合完成 prompt 切换。
    """

    def __init__(self):
        """
        初始化财商分析专用 agent。
        """
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_finance_agent_prompt(),
            tools=[
                get_current_time,
                build_finance_evidence_pack,
                get_all_data,
                rag_summarize,
                fill_context_for_report,
                record_income,
                adjust_account_balance,
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

        # Phase 2 的推荐链与评估链不再强依赖工具型 ReAct 循环，
        # 而是采用“程序先准备数据包，再让模型在受限上下文里做最终判断”的方式。
        self.card_recommendation_chain = (
            PromptTemplate.from_template(load_card_recommendation_prompt())
            | chat_model
            | StrOutputParser()
        )
        self.card_evaluation_chain = (
            PromptTemplate.from_template(load_card_evaluation_prompt())
            | chat_model
            | StrOutputParser()
        )

    @staticmethod
    def _extract_text_content(message: Any) -> str:
        """
        从不同形态的消息 content 中提取可展示文本。

        说明：
        - create_agent 的流式 chunk 中，content 可能是字符串；
        - 也可能是分块结构列表；
        - 这里统一收敛成纯文本，便于页面直接流式展示。
        """
        content = getattr(message, "content", "")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                    continue

                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        text_parts.append(str(item.get("text")))
                    elif item.get("content"):
                        text_parts.append(str(item.get("content")))

            return "".join(text_parts).strip()

        return str(content).strip() if content is not None else ""

    @staticmethod
    def _build_tool_status_message(tool_name: str, tool_args: dict | None = None, completed: bool = False, evidence_pack_result: str = None) -> str:
        """
        为页面侧的"过程展示区"生成更友好的工具调用状态文案。
        
        优化说明：减少emoji使用，使用更简洁的文字描述。
        """
        import json
        tool_args = tool_args or {}

        if completed:
            if tool_name == "get_current_time":
                current_time = tool_args.get("current_time", "")
                if current_time:
                    return f"[完成] 当前时间：{current_time}"
                return "[完成] 已获取当前时间"

            if tool_name == "build_finance_evidence_pack":
                if evidence_pack_result:
                    try:
                        if isinstance(evidence_pack_result, str):
                            pack = json.loads(evidence_pack_result)
                        else:
                            pack = evidence_pack_result
                        
                        data_avail = pack.get("data_availability", {})
                        selected_summary = pack.get("selected_summary", {})
                        task_meta = pack.get("task_meta", {})
                        
                        txn_count = data_avail.get("selected_transaction_count", 0)
                        total_amount = selected_summary.get("total_amount", 0)
                        top_cats = selected_summary.get("top_categories", [])
                        top_cats_str = "、".join([c.get("name", "") for c in top_cats[:3]]) if top_cats else "暂无"
                        
                        time_label = task_meta.get("time_label", "")
                        
                        lines = [
                            f"[完成] 数据聚合",
                            f"    共 {txn_count} 笔交易，总支出 ¥{total_amount:.2f}",
                            f"    主要类别：{top_cats_str}",
                        ]
                        if time_label:
                            lines.append(f"    时间：{time_label}")
                        
                        return "\n".join(lines)
                    except Exception:
                        pass
                return "[完成] 已完成消费数据聚合"

            if tool_name == "rag_summarize":
                return "[完成] 已检索财商知识支持"

            if tool_name == "fill_context_for_report":
                return "[完成] 正在切换到报告模式"

            if tool_name == "build_card_candidates":
                return "[完成] 已筛选知识卡片候选"

            if tool_name == "build_card_evaluation_pack":
                return "[完成] 已构建评估数据包"

            if tool_name == "record_income":
                return "[完成] 已记录收入并分配账户"

            if tool_name == "adjust_account_balance":
                return "[完成] 已调整账户余额"

            return f"[完成] {tool_name}"

        # ===== 以下是工具调用前的状态提示（未完成）=====
        
        if tool_name == "get_current_time":
            return "正在获取当前时间..."

        if tool_name == "build_finance_evidence_pack":
            start_date = tool_args.get("start_date")
            end_date = tool_args.get("end_date")
            category = tool_args.get("category")
            subcategory = tool_args.get("subcategory")
            user_query = tool_args.get("user_query", "")

            scope_parts = []
            if start_date or end_date:
                scope_parts.append(f"{start_date or '历史起点'} ~ {end_date or '当前'}")
            else:
                scope_parts.append("全部历史数据")

            if category:
                scope_parts.append(f"类别：{category}")
            if subcategory:
                scope_parts.append(f"子类别：{subcategory}")
            
            lines = ["正在聚合消费数据..."]
            lines.append("    " + "，".join(scope_parts))
            if user_query and len(user_query) < 50:
                lines.append(f"    目标：{user_query}")
            
            return "\n".join(lines)

        if tool_name == "rag_summarize":
            return "正在检索财商知识支持..."

        if tool_name == "fill_context_for_report":
            return "证据已足够，切换到报告模式..."

        if tool_name == "build_card_candidates":
            return "正在筛选知识卡片候选..."

        if tool_name == "build_card_evaluation_pack":
            return "正在构建评估数据包..."

        if tool_name == "record_income":
            source = tool_args.get("source", "未知来源")
            amount = tool_args.get("amount", 0)
            return f"正在记录收入：{source} ¥{amount}..."

        if tool_name == "adjust_account_balance":
            account_type = tool_args.get("account_type", "")
            change_amount = tool_args.get("change_amount", 0)
            account_name = "储蓄账户" if account_type == "savings" else "流动资金"
            return f"正在调整{account_name}余额..."

        return f"正在调用：{tool_name}"

    @staticmethod
    def _parse_json_object(raw_text: str) -> Optional[dict]:
        """
        兼容模型返回 ```json 包裹或前后夹杂说明文本的情况。
        """
        if not raw_text:
            return None

        candidate_text = str(raw_text).strip()
        candidate_text = re.sub(r"^```json\s*", "", candidate_text, flags=re.IGNORECASE)
        candidate_text = re.sub(r"^```\s*", "", candidate_text)
        candidate_text = re.sub(r"\s*```$", "", candidate_text)

        try:
            parsed_value = json.loads(candidate_text)
            return parsed_value if isinstance(parsed_value, dict) else None
        except json.JSONDecodeError:
            pass

        start_index = candidate_text.find("{")
        end_index = candidate_text.rfind("}")
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            return None

        try:
            parsed_value = json.loads(candidate_text[start_index:end_index + 1])
            return parsed_value if isinstance(parsed_value, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _format_history_excerpt(history: list | None, limit: int = 4) -> str:
        if not history:
            return "无"

        excerpt_lines = []
        for message in history[-limit:]:
            role = str(message.get("role", "assistant"))
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            excerpt_lines.append(f"[{role}] {content}")

        return "\n".join(excerpt_lines) if excerpt_lines else "无"

    @staticmethod
    def _format_tracked_card_state(user_id: Optional[str]) -> str:
        if not user_id:
            return "无"

        state_manager = CardStateManager(user_id)
        tracked_cards = state_manager.get_active_cards()
        if not tracked_cards:
            return "无"

        lines = []
        for card in tracked_cards[:5]:
            lines.append(
                f"- {card.get('card_title', '未命名卡片')}｜状态={card.get('status', 'unknown')}｜"
                f"next={card.get('next_evaluation_date', '未设置')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _build_card_recommendation_fallback(candidate_result: dict) -> dict:
        candidates = candidate_result.get("candidates", [])
        if not candidates:
            return {
                "should_recommend": False,
                "selected_card_id": "",
                "selection_reason": "当前没有足够匹配的卡片候选。",
                "display_summary": {},
            }

        best_candidate = candidates[0]
        if float(best_candidate.get("match_score", 0.0) or 0.0) < 2.2:
            return {
                "should_recommend": False,
                "selected_card_id": "",
                "selection_reason": "当前候选卡片与问题的匹配度还不够强，先不强推学习卡片。",
                "display_summary": {},
            }

        card_payload = best_candidate.get("card_payload", {})
        return {
            "should_recommend": True,
            "selected_card_id": card_payload.get("card_id", ""),
            "selection_reason": "当前问题信号和消费焦点与这张卡片最匹配，适合先从这一条小行动开始。",
            "display_summary": {
                "title": card_payload.get("title", ""),
                "tags": card_payload.get("tags", []),
                "doing_text": card_payload.get("doing_text", ""),
                "why_text": card_payload.get("why_text", ""),
                "professional_term": card_payload.get("professional_term", ""),
                "authority_source": card_payload.get("authority_source", ""),
                "recommended_eval_days": card_payload.get("recommended_eval_days", 7),
            },
        }

    @staticmethod
    def _build_card_evaluation_fallback(evaluation_pack: dict) -> dict:
        current_pack = evaluation_pack.get("current_pack", {})
        previous_pack = evaluation_pack.get("previous_pack", {})

        current_amount = float(current_pack.get("total_amount", 0.0) or 0.0)
        previous_amount = float(previous_pack.get("total_amount", 0.0) or 0.0)
        current_count = int(current_pack.get("transaction_count", 0) or 0)
        previous_count = int(previous_pack.get("transaction_count", 0) or 0)

        if current_count == 0 and previous_count == 0:
            return {
                "evaluation_result": "insufficient_data",
                "confidence": "low",
                "reason": "当前周期和前一周期都缺少足够的相关交易，暂时看不出稳定趋势。",
                "next_action": "continue_tracking",
                "suggested_next_eval_days": 7,
                "user_facing_summary": "这张卡片目前还缺少足够的数据来判断效果，建议再继续观察一周。",
            }

        if current_count == 0 and previous_count > 0:
            return {
                "evaluation_result": "completed",
                "confidence": "medium",
                "reason": "当前观察周期内已经没有继续出现这类消费，说明行为有明显收敛。",
                "next_action": "complete_card",
                "suggested_next_eval_days": 7,
                "user_facing_summary": "这张卡片对应的消费行为已经明显收住了，可以先视为完成。",
            }

        if previous_count > 0 and (current_count < previous_count or current_amount < previous_amount):
            return {
                "evaluation_result": "improved",
                "confidence": "medium",
                "reason": "和前一个等长周期相比，相关消费的次数或金额已经有下降。",
                "next_action": "continue_tracking",
                "suggested_next_eval_days": 7,
                "user_facing_summary": "这张卡片已经出现一些改善，但还可以再观察一周，让变化更稳定。",
            }

        return {
            "evaluation_result": "not_improved",
            "confidence": "medium",
            "reason": "当前周期和前一周期相比，没有看到明显下降，说明这条习惯还没有真正稳住。",
            "next_action": "continue_tracking",
            "suggested_next_eval_days": 7,
            "user_facing_summary": "这张卡片对应的行为暂时还没有明显改善，建议继续追踪一周并把行动做得更具体一点。",
        }

    @staticmethod
    def _build_evaluation_markdown(evaluation_result: dict, evaluation_pack: dict) -> str:
        current_pack = evaluation_pack.get("current_pack", {})
        previous_pack = evaluation_pack.get("previous_pack", {})
        card_payload = evaluation_pack.get("card_payload", {})

        next_action_map = {
            "complete_card": "先把这张卡片标记为完成。",
            "continue_tracking": "继续追踪一段时间，看看变化能不能稳定下来。",
            "snooze_card": "先把这张卡片放缓一下，之后再看。",
        }

        return (
            "## 评估结论\n"
            f"- {evaluation_result.get('user_facing_summary', '这张卡片已经完成本轮检查。')}\n"
            f"- 当前评估结果：{evaluation_result.get('evaluation_result', 'unknown')}，置信度：{evaluation_result.get('confidence', 'medium')}。\n\n"
            "## 观察到的变化\n"
            f"- 当前周期：{current_pack.get('window', {}).get('label', '当前窗口')}，相关交易 {current_pack.get('transaction_count', 0)} 笔，总金额 ¥{float(current_pack.get('total_amount', 0.0) or 0.0):.2f}。\n"
            f"- 前一周期：{previous_pack.get('window', {}).get('label', '前一窗口')}，相关交易 {previous_pack.get('transaction_count', 0)} 笔，总金额 ¥{float(previous_pack.get('total_amount', 0.0) or 0.0):.2f}。\n"
            f"- 判断依据：{evaluation_result.get('reason', '本轮数据不足，暂时无法给出更强判断。')}\n\n"
            "## 下一步建议\n"
            f"- 当前卡片：{card_payload.get('title', '未命名卡片')}。\n"
            f"- 继续动作：{card_payload.get('doing_text', '保持这条行动并继续观察。')}\n"
            f"- 系统建议：{next_action_map.get(evaluation_result.get('next_action'), '继续保持观察。')}"
        )

    def execute_stream_with_events(self,
                                   query: str,
                                   history: list | None = None,
                                   runtime_context: Optional[dict] = None):
        """
        执行带事件流的财商分析。

        事件类型：
        - status: 给页面展示“当前做到哪一步了”
        - answer: 给页面展示最终报告内容
        """
        # 一进入流程，先给页面一个通用启动提示。
        yield {
            "type": "status",
            "stage": "start",
            "content": "正在理解你的问题..."
        }

        # 先构建完整消息序列，让 agent 能基于历史进行追问承接。
        input_messages = []
        if history:
            input_messages.extend(history)
        input_messages.append({"role": "user", "content": query})

        # 为当前财商 agent 准备最小运行时状态。
        merged_context = {
            "report": False,
            "agent_scene": "finance_assistant",
        }
        if runtime_context:
            merged_context.update(runtime_context)
            merged_context["agent_scene"] = "finance_assistant"
            merged_context["report"] = False

        last_emitted_text = ""
        report_started = False
        fallback_final_text = ""
        has_seen_tool_message = False
        has_seen_tool_call = False
        pending_tool_names: list[str] = []

        try:
            for chunk in self.agent.stream(
                cast(Any, {"messages": input_messages}),
                stream_mode="values",
                context=cast(Any, merged_context),
            ):
                latest_message = chunk["messages"][-1]
                latest_message_type = type(latest_message).__name__

                if latest_message_type == "ToolMessage":
                    has_seen_tool_message = True
                    completed_tool_name = pending_tool_names.pop(0) if pending_tool_names else "unknown_tool"
                    tool_output_text = self._extract_text_content(latest_message)

                    if completed_tool_name == "fill_context_for_report":
                        report_started = True

                    if completed_tool_name in {"build_finance_evidence_pack", "rag_summarize", "build_card_candidates", "build_card_evaluation_pack"}:
                        yield {
                            "type": "artifact",
                            "name": completed_tool_name,
                            "content": tool_output_text,
                        }

                    yield {
                        "type": "status",
                        "stage": "tool_completed",
                        "content": self._build_tool_status_message(completed_tool_name, completed=True),
                    }
                    continue

                if latest_message_type == "HumanMessage":
                    continue

                latest_tool_calls = getattr(latest_message, "tool_calls", None)
                if latest_tool_calls:
                    has_seen_tool_call = True
                    for tool_call in latest_tool_calls:
                        tool_name = tool_call.get("name", "unknown_tool")
                        tool_args = tool_call.get("args", {})
                        pending_tool_names.append(tool_name)

                        yield {
                            "type": "status",
                            "stage": "tool_call",
                            "content": self._build_tool_status_message(tool_name, tool_args=tool_args, completed=False),
                        }
                    continue

                current_text = self._extract_text_content(latest_message)
                if not current_text:
                    continue

                # 不管是否调用过工具，只要当前出现了一个无 tool_call 的 AI 最终文本，
                # 都先缓存为兜底结果。
                fallback_final_text = current_text

                if not report_started:
                    continue

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
            return

        if not report_started and fallback_final_text:
            # 轻量问题可能完全不需要工具；
            # 数据分析问题则可能在工具后直接给出一个最终简答。
            fallback_status_text = (
                "[轻量回答] 这个问题不需要读取你的消费数据。"
                if not has_seen_tool_call else
                "[完成] 当前场景已直接得到最终结果。"
            )
            yield {
                "type": "status",
                "stage": "fallback_final",
                "content": fallback_status_text
            }
            yield {
                "type": "answer",
                "content": fallback_final_text,
            }

    def execute_card_recommendation(self,
                                    query: str,
                                    evidence_pack_json: str,
                                    analysis_summary: str = "",
                                    history: list | None = None,
                                    runtime_context: dict | None = None) -> dict:
        """
        在程序预筛后的少量候选卡片中，让模型做最终单卡选择。
        """
        candidate_result = self._parse_json_object(
            build_card_candidates.invoke({
                "user_query": query,
                "evidence_pack_json": evidence_pack_json,
                "max_candidates": 5,
            })
        ) or {"success": False, "candidate_count": 0, "candidates": []}

        if not candidate_result.get("success") or not candidate_result.get("candidates"):
            return {
                "should_recommend": False,
                "selected_card": None,
                "selection_reason": "当前没有明显合适的知识卡片候选。",
                "candidate_count": 0,
            }

        try:
            raw_response = self.card_recommendation_chain.invoke({
                "user_query": query,
                "analysis_summary": analysis_summary or "暂无额外分析摘要",
                "evidence_pack": evidence_pack_json,
                "candidate_cards": json.dumps(candidate_result.get("candidates", []), ensure_ascii=False, indent=2),
                "active_card_state": self._format_tracked_card_state((runtime_context or {}).get("user_id")),
            })
            parsed_response = self._parse_json_object(raw_response)
        except Exception:
            parsed_response = None

        if not parsed_response:
            parsed_response = self._build_card_recommendation_fallback(candidate_result)

        candidate_map = {
            candidate.get("card_id"): candidate
            for candidate in candidate_result.get("candidates", [])
        }
        selected_card_id = str(parsed_response.get("selected_card_id", "")).strip()
        selected_candidate = candidate_map.get(selected_card_id)

        if not parsed_response.get("should_recommend") or not selected_candidate:
            if not selected_candidate and parsed_response.get("should_recommend"):
                parsed_response = self._build_card_recommendation_fallback(candidate_result)
                selected_card_id = str(parsed_response.get("selected_card_id", "")).strip()
                selected_candidate = candidate_map.get(selected_card_id)

        if not parsed_response.get("should_recommend") or not selected_candidate:
            return {
                "should_recommend": False,
                "selected_card": None,
                "selection_reason": parsed_response.get("selection_reason", "当前不建议强行推荐知识卡片。"),
                "candidate_count": candidate_result.get("candidate_count", 0),
            }

        card_payload = selected_candidate.get("card_payload", {})
        
        # 传递是否已在学习计划中的状态，供页面层展示不同UI
        is_already_tracked = selected_candidate.get("is_already_tracked", False)
        tracked_instance = selected_candidate.get("tracked_instance")
        
        return {
            "should_recommend": True,
            "selected_card": {
                **card_payload,
                "recommended_eval_days": card_payload.get("recommended_eval_days", 7),
            },
            "selection_reason": parsed_response.get("selection_reason", "这张卡片与当前问题最相关。"),
            "candidate_count": candidate_result.get("candidate_count", 0),
            "is_already_tracked": is_already_tracked,
            "tracked_instance": tracked_instance,
        }

    def execute_card_evaluation_stream(self,
                                       card_instance_id: str,
                                       history: list | None = None,
                                       runtime_context: dict | None = None):
        """
        执行知识卡片评估流程，并以事件流形式返回过程状态与最终结果。
        """
        yield {
            "type": "status",
            "stage": "start",
            "content": "正在检查知识卡片的评估窗口，准备对比数据...",
        }

        try:
            evaluation_pack_json = build_card_evaluation_pack.invoke({
                "card_instance_id": card_instance_id,
            })
            yield {
                "type": "artifact",
                "name": "build_card_evaluation_pack",
                "content": evaluation_pack_json,
            }
            yield {
                "type": "status",
                "stage": "tool_completed",
                "content": "[完成] 已拿到当前周期与前一周期的卡片评估数据。",
            }
        except Exception as error:
            normalized_error = normalize_model_error(error)
            yield {
                "type": "error",
                "stage": "build_evaluation_pack_error",
                "content": normalized_error["status_message"],
            }
            yield {
                "type": "answer",
                "content": normalized_error["user_message"],
            }
            return

        evaluation_pack = self._parse_json_object(evaluation_pack_json)
        if not evaluation_pack or not evaluation_pack.get("success"):
            error_message = "当前没有成功构建卡片评估数据包。"
            if evaluation_pack:
                error_message = str(evaluation_pack.get("error") or error_message)
            yield {
                "type": "error",
                "stage": "evaluation_pack_invalid",
                "content": error_message,
            }
            yield {
                "type": "answer",
                "content": f"这次卡片评估暂时没能完成：{error_message}",
            }
            return

        yield {
            "type": "status",
            "stage": "llm_evaluation",
            "content": "正在结合卡片目标和前后周期数据，判断改善情况...",
        }

        try:
            raw_response = self.card_evaluation_chain.invoke({
                "card_instance": json.dumps(evaluation_pack.get("card_instance", {}), ensure_ascii=False, indent=2),
                "card_payload": json.dumps(evaluation_pack.get("card_payload", {}), ensure_ascii=False, indent=2),
                "current_pack": json.dumps(evaluation_pack.get("current_pack", {}), ensure_ascii=False, indent=2),
                "previous_pack": json.dumps(evaluation_pack.get("previous_pack", {}), ensure_ascii=False, indent=2),
            })
            evaluation_result = self._parse_json_object(raw_response)
        except Exception:
            evaluation_result = None

        if not evaluation_result:
            evaluation_result = self._build_card_evaluation_fallback(evaluation_pack)

        final_markdown = self._build_evaluation_markdown(evaluation_result, evaluation_pack)
        yield {
            "type": "result",
            "content": evaluation_result,
        }
        yield {
            "type": "answer",
            "content": final_markdown,
        }

    def execute_stream(self,
                       query: str,
                       history: list | None = None,
                       runtime_context: Optional[dict] = None):
        """
        兼容旧调用方式：只返回最终答案文本，不返回过程事件。
        """
        for event in self.execute_stream_with_events(
            query=query,
            history=history,
            runtime_context=runtime_context,
        ):
            if event.get("type") == "answer":
                yield event.get("content", "")



