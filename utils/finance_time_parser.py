"""
财商助手时间范围解析器
负责将自然语言时间表达转换成结构化的起止日期
"""

from __future__ import annotations

import calendar
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

try:
    from ..model.factory import chat_model
    from .prompt_loader import load_finance_time_parse_prompt
except ImportError:
    from importlib import import_module

    chat_model = import_module("model.factory").chat_model
    load_finance_time_parse_prompt = import_module("utils.prompt_loader").load_finance_time_parse_prompt


@dataclass
class TimeParseResult:
    """
    时间解析结果对象。
    """
    type: str
    label: str
    start_date: Optional[str]
    end_date: Optional[str]
    explicit: bool
    window_days: Optional[int]
    source: str
    confidence: str

    def to_dict(self) -> dict:
        """
        转成 analysis_query_parser 可直接使用的字典结构。
        """
        return {
            "type": self.type,
            "label": self.label,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "explicit": self.explicit,
            "window_days": self.window_days,
            "source": self.source,
            "confidence": self.confidence,
        }


class FinanceTimeParser:
    """
    财商助手时间解析器。

    设计原则：
    - 高频时间表达优先走规则解析，速度快且稳定；
    - 复杂时间表达交给 LLM 兜底；
    - LLM 的输出必须经过程序校验，不能直接信任。
    """

    SIMPLE_KEYWORDS = {
        "this_year": ["今年", "本年", "今年以来", "年度", "全年"],
        "last_year": ["去年", "上年", "上一年"],
        "last_month": ["上个月", "上月"],
        "this_month": ["这个月", "本月"],
        "recent_7_days": ["最近7天", "近7天", "最近一周", "近一周", "这周", "本周"],
        "recent_30_days": ["最近30天", "近30天", "最近一个月", "近一个月"],
        "all": ["全部", "所有", "全部消费", "所有消费", "历史消费", "历史记录"],
    }

    def __init__(self):
        """
        初始化时间解析器。
        """
        self.prompt_text = load_finance_time_parse_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self.prompt_template | self.model | StrOutputParser()

    def resolve_time_range(self, query: str, today: Optional[date] = None) -> dict:
        """
        将自然语言时间表达解析成结构化范围。

        解析顺序：
        1. 规则解析
        2. LLM 兜底解析
        3. 默认最近 30 天
        """
        today = today or date.today()
        normalized_query = query.strip()

        rule_result = self._parse_by_rules(normalized_query, today=today)
        if rule_result is not None:
            return rule_result.to_dict()

        llm_result = self._parse_by_llm(normalized_query, today=today)
        if llm_result is not None:
            return llm_result.to_dict()

        start_date = today - timedelta(days=29)
        return TimeParseResult(
            type="recent_30_days",
            label="最近 30 天（默认）",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d"),
            explicit=False,
            window_days=30,
            source="default",
            confidence="low",
        ).to_dict()

    def _parse_by_rules(self, query: str, today: date) -> Optional[TimeParseResult]:
        """
        高频时间表达优先走规则解析。
        """
        # 1. 先处理相对稳定的“去年3月 / 2025年3月”这类月份表达
        month_result = self._parse_specific_month(query, today)
        if month_result is not None:
            return month_result

        # 2. 处理“这个月上旬 / 中旬 / 下旬”这类旬表达
        period_result = self._parse_month_period(query, today)
        if period_result is not None:
            return period_result

        # 3. 处理“这三个月 / 前四个月 / 最近45天”这类区间表达
        rolling_result = self._parse_rolling_range(query, today)
        if rolling_result is not None:
            return rolling_result

        # 4. 处理当前已经有的简单关键词
        for range_type, keyword_list in self.SIMPLE_KEYWORDS.items():
            if any(keyword in query for keyword in keyword_list):
                if range_type == "this_year":
                    return TimeParseResult(
                        type="this_year",
                        label="今年",
                        start_date=f"{today.year}-01-01",
                        end_date=today.strftime("%Y-%m-%d"),
                        explicit=True,
                        window_days=None,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "last_year":
                    return TimeParseResult(
                        type="last_year",
                        label="去年",
                        start_date=f"{today.year - 1}-01-01",
                        end_date=f"{today.year - 1}-12-31",
                        explicit=True,
                        window_days=None,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "last_month":
                    target_year = today.year
                    target_month = today.month - 1
                    if target_month == 0:
                        target_year -= 1
                        target_month = 12
                    start_date, end_date = self._month_range(target_year, target_month)
                    return TimeParseResult(
                        type="last_month",
                        label="上个月",
                        start_date=start_date,
                        end_date=end_date,
                        explicit=True,
                        window_days=None,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "this_month":
                    start_date, end_date = self._month_range(today.year, today.month)
                    return TimeParseResult(
                        type="this_month",
                        label="本月",
                        start_date=start_date,
                        end_date=min(end_date, today.strftime("%Y-%m-%d")),
                        explicit=True,
                        window_days=None,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "recent_7_days":
                    start_date = today - timedelta(days=6)
                    return TimeParseResult(
                        type="recent_7_days",
                        label="最近 7 天",
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=today.strftime("%Y-%m-%d"),
                        explicit=True,
                        window_days=7,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "recent_30_days":
                    start_date = today - timedelta(days=29)
                    return TimeParseResult(
                        type="recent_30_days",
                        label="最近 30 天",
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=today.strftime("%Y-%m-%d"),
                        explicit=True,
                        window_days=30,
                        source="rule",
                        confidence="high",
                    )

                if range_type == "all":
                    return TimeParseResult(
                        type="all",
                        label="全部历史数据",
                        start_date=None,
                        end_date=None,
                        explicit=True,
                        window_days=None,
                        source="rule",
                        confidence="high",
                    )

        return None

    def _parse_specific_month(self, query: str, today: date) -> Optional[TimeParseResult]:
        """
        解析具体月份表达，例如：
        - 去年3月
        - 2025年3月
        - 今年3月
        - 3月（带较弱默认）
        """
        normalized_query = query.replace(" ", "")

        match = re.search(r"(?:(\d{4})年|今年|去年)?(\d{1,2})月", normalized_query)
        if not match:
            return None

        raw_year = match.group(1)
        target_month = int(match.group(2))
        if not 1 <= target_month <= 12:
            return None

        if raw_year:
            target_year = int(raw_year)
        elif "去年" in normalized_query:
            target_year = today.year - 1
        elif "今年" in normalized_query:
            target_year = today.year
        else:
            # 当用户只说“3月”，第一版默认优先取当前年份；
            # 如果当前还没到 3 月，则取上一年，尽量减少未来时间范围。
            target_year = today.year if today.month >= target_month else today.year - 1

        start_date, end_date = self._month_range(target_year, target_month)
        end_date = min(end_date, today.strftime("%Y-%m-%d")) if target_year == today.year and target_month == today.month else end_date

        if "去年" in normalized_query:
            label = f"去年 {target_month} 月"
            time_type = "last_year_month"
        elif "今年" in normalized_query:
            label = f"今年 {target_month} 月"
            time_type = "this_year_month"
        else:
            label = f"{target_year}-{target_month:02d}"
            time_type = "specific_month"

        return TimeParseResult(
            type=time_type,
            label=label,
            start_date=start_date,
            end_date=end_date,
            explicit=True,
            window_days=None,
            source="rule",
            confidence="high",
        )

    def _parse_month_period(self, query: str, today: date) -> Optional[TimeParseResult]:
        """
        解析“上旬 / 中旬 / 下旬”。
        """
        normalized_query = query.replace(" ", "")
        period_name = None
        if "上旬" in normalized_query:
            period_name = "上旬"
            start_day, end_day = 1, 10
        elif "中旬" in normalized_query:
            period_name = "中旬"
            start_day, end_day = 11, 20
        elif "下旬" in normalized_query:
            period_name = "下旬"
            start_day, end_day = 21, calendar.monthrange(today.year, today.month)[1]
        else:
            return None

        target_year = today.year
        target_month = today.month
        if "上个月" in normalized_query or "上月" in normalized_query:
            target_month -= 1
            if target_month == 0:
                target_month = 12
                target_year -= 1
        elif "去年" in normalized_query:
            target_year -= 1

        last_day = calendar.monthrange(target_year, target_month)[1]
        end_day = min(end_day, last_day)
        start_date = date(target_year, target_month, start_day)
        end_date = date(target_year, target_month, end_day)

        if target_year == today.year and target_month == today.month and end_date > today:
            end_date = today

        label_prefix = "本月"
        if "上个月" in normalized_query or "上月" in normalized_query:
            label_prefix = "上个月"
        elif "去年" in normalized_query and "月" not in normalized_query:
            label_prefix = "去年同月"

        return TimeParseResult(
            type="month_period",
            label=f"{label_prefix}{period_name}",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            explicit=True,
            window_days=None,
            source="rule",
            confidence="high",
        )

    def _parse_rolling_range(self, query: str, today: date) -> Optional[TimeParseResult]:
        """
        解析“这三个月 / 前四个月 / 最近45天”这类表达。
        """
        normalized_query = query.replace(" ", "")

        recent_day_match = re.search(r"(?:最近|近)(\d{1,3})天", normalized_query)
        if recent_day_match:
            days = int(recent_day_match.group(1))
            if days > 0:
                start_date = today - timedelta(days=days - 1)
                return TimeParseResult(
                    type="recent_n_days",
                    label=f"最近 {days} 天",
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=today.strftime("%Y-%m-%d"),
                    explicit=True,
                    window_days=days,
                    source="rule",
                    confidence="high",
                )

        month_window_match = re.search(r"(?:这|近|最近|前)([一二两三四五六七八九十\d]{1,3})个?月", normalized_query)
        if month_window_match:
            month_count = self._parse_chinese_or_digit_number(month_window_match.group(1))
            if month_count and month_count > 0:
                start_year, start_month = self._shift_month(today.year, today.month, -(month_count - 1))
                start_date = f"{start_year}-{start_month:02d}-01"
                return TimeParseResult(
                    type="recent_n_months",
                    label=f"最近 {month_count} 个月",
                    start_date=start_date,
                    end_date=today.strftime("%Y-%m-%d"),
                    explicit=True,
                    window_days=None,
                    source="rule",
                    confidence="medium",
                )

        return None

    def _parse_by_llm(self, query: str, today: date) -> Optional[TimeParseResult]:
        """
        对规则未覆盖的复杂时间表达，使用 LLM 做兜底解析。
        """
        try:
            raw_result = self.chain.invoke({
                "today": today.strftime("%Y-%m-%d"),
                "query": query,
            })
            parsed_json = json.loads(raw_result)
        except Exception:
            return None

        if not isinstance(parsed_json, dict) or not parsed_json.get("matched"):
            return None

        start_date = str(parsed_json.get("start_date", "")).strip()
        end_date = str(parsed_json.get("end_date", "")).strip()
        if not self._is_valid_date_string(start_date) or not self._is_valid_date_string(end_date):
            return None

        start_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        if start_obj > end_obj:
            return None

        if end_obj > today:
            end_obj = today
        if start_obj > today:
            return None

        return TimeParseResult(
            type=str(parsed_json.get("time_type", "time_range_llm")).strip() or "time_range_llm",
            label=str(parsed_json.get("label", "自定义时间范围")).strip() or "自定义时间范围",
            start_date=start_obj.strftime("%Y-%m-%d"),
            end_date=end_obj.strftime("%Y-%m-%d"),
            explicit=True,
            window_days=(end_obj - start_obj).days + 1,
            source="llm",
            confidence="medium",
        )

    @staticmethod
    def _month_range(target_year: int, target_month: int) -> tuple[str, str]:
        """
        获取自然月起止日期。
        """
        last_day = calendar.monthrange(target_year, target_month)[1]
        start_date = date(target_year, target_month, 1)
        end_date = date(target_year, target_month, last_day)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    @staticmethod
    def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
        """
        对年月做月级偏移。
        """
        absolute_month = year * 12 + (month - 1) + offset
        shifted_year = absolute_month // 12
        shifted_month = absolute_month % 12 + 1
        return shifted_year, shifted_month

    @staticmethod
    def _is_valid_date_string(value: str) -> bool:
        """
        校验字符串是否为 YYYY-MM-DD 日期格式。
        """
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _parse_chinese_or_digit_number(raw_value: str) -> Optional[int]:
        """
        解析中文数字或阿拉伯数字。
        """
        normalized = str(raw_value).strip()
        if not normalized:
            return None

        if normalized.isdigit():
            return int(normalized)

        chinese_map = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }

        if normalized == "十":
            return 10
        if normalized in chinese_map:
            return chinese_map[normalized]
        if len(normalized) == 2 and normalized[0] == "十" and normalized[1] in chinese_map:
            return 10 + chinese_map[normalized[1]]

        return None


if __name__ == "__main__":
    parser = FinanceTimeParser()
    for query_text in [
        "分析我去年3月的数据",
        "分析我这三个月的消费",
        "分析我这个月上旬的消费",
    ]:
        print(query_text, parser.resolve_time_range(query_text))

